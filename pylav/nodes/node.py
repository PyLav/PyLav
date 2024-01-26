from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import datetime
import functools
import logging
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

import aiohttp
from aiohttp.helpers import sentinel  # noqa:
from apscheduler.jobstores.base import JobLookupError
from dacite import from_dict
from expiringdict import ExpiringDict
from multidict import CIMultiDictProxy
from packaging.version import Version, parse
from yarl import URL

from pylav.compat import json
from pylav.constants.builtin_nodes import BUNDLED_NODES_IDS_HOST_MAPPING, PYLAV_NODES
from pylav.constants.coordinates import REGION_TO_COUNTRY_COORDINATE_MAPPING
from pylav.constants.node import GOOD_RESPONSE_RANGE, MAX_SUPPORTED_API_MAJOR_VERSION
from pylav.constants.node_features import SUPPORTED_FEATURES, SUPPORTED_SOURCES
from pylav.constants.regex import SEMANTIC_VERSIONING
from pylav.events.api import LavalinkLoadSearchEvent, LavalinkLoadtracksEvent
from pylav.events.base import PyLavEvent
from pylav.exceptions.request import HTTPException, UnauthorizedException
from pylav.helpers.time import get_now_utc
from pylav.logging import getLogger
from pylav.nodes.api.responses import rest_api
from pylav.nodes.api.responses import websocket as websocket_responses
from pylav.nodes.api.responses.errors import LavalinkError
from pylav.nodes.api.responses.rest_api import PlaylistData
from pylav.nodes.api.responses.route_planner import Status as RoutePlannerStart
from pylav.nodes.api.responses.track import Track
from pylav.nodes.utils import EMPTY_RESPONSE, Stats
from pylav.nodes.websocket import WebSocket
from pylav.players.filters import (
    ChannelMix,
    Distortion,
    Echo,
    Equalizer,
    Karaoke,
    LowPass,
    Rotation,
    Timescale,
    Tremolo,
    Vibrato,
    Volume,
)
from pylav.players.query.obj import Query
from pylav.storage.models.node import mocked as node_mocked
from pylav.storage.models.node import real as node_real
from pylav.type_hints.dict_typing import JSON_DICT_TYPE
from pylav.utils.location import distance

if TYPE_CHECKING:
    from pylav.nodes.manager import NodeManager
    from pylav.players.player import Player


class Node:
    """Represents a Node connection with Lavalink.

    Note
    ----
    Nodes are **NOT** meant to be added manually, but rather with :func:`Client.add_node`.
    """

    __slots__ = (
        "_query_cls",
        "_manager",
        "_session",
        "_temporary",
        "_host",
        "_port",
        "_password",
        "_name",
        "_ssl",
        "_config",
        "_managed",
        "_region",
        "_extras",
        "_stats",
        "_disabled_sources",
        "_identifier",
        "_resume_timeout",
        "_reconnect_attempts",
        "_search_only",
        "_capabilities",
        "_coordinates",
        "_down_votes",
        "_ready",
        "_ws",
        "_version",
        "_api_version",
        "_logger",
        "_filters",
        "__cli_flags",
    )

    def __init__(
        self,
        manager: NodeManager,
        host: str,
        password: str,
        resume_timeout: int,
        port: int | None = None,
        name: str | None = None,
        reconnect_attempts: int = -1,
        ssl: bool = False,
        search_only: bool = False,
        unique_identifier: int = None,
        disabled_sources: list[str] = None,
        managed: bool = False,
        extras: dict = None,
        temporary: bool = False,
    ) -> None:
        self._query_cls: Query = Query  # type: ignore
        self._version: Version | None = None
        self._api_version: int | None = None
        self._manager = manager
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120), json_serialize=json.dumps)
        self._temporary = temporary
        if not temporary:
            # noinspection PyProtectedMember
            self._config: node_real.Node = self._manager._client.node_db_manager.get_node_config(unique_identifier)
        else:
            self._config: node_mocked.NodeMock | None = None
        if unique_identifier is None:
            unique_identifier = str(uuid4())
        self._managed = managed
        self._region = None
        self._host = host
        self._name = name or f"{self._region}-{self._host}-{unique_identifier}"
        self._extras = extras or {}
        self._disabled_sources = set(disabled_sources or [])

        self._logger = getLogger(f"PyLav.Node-{self._name}")

        if self._manager.get_node_by_id(unique_identifier) is not None:
            raise ValueError(f"A Node with identifier:{unique_identifier} already exists")
        self._identifier = unique_identifier
        self._ssl = ssl
        if port is None:
            self._port = 443 if self._ssl else 80
        else:
            self._port = port
        self._password = password

        self._resume_timeout = resume_timeout
        self._reconnect_attempts = reconnect_attempts
        self._search_only = search_only
        self._capabilities: set[str] = set()
        self._filters: set[str] = set()
        self._coordinates = (0, 0)
        self._down_votes = ExpiringDict(max_len=float("inf"), max_age_seconds=600)  # type: ignore
        self.__cli_flags = getattr("manager._client.bot", "_cli_flags", None)

        self._stats = None

        self._ready = asyncio.Event()
        self._ws = WebSocket(
            node=self,
            host=self.host,
            port=self.port,
            password=self.password,
            resume_timeout=self.resume_timeout,
            reconnect_attempts=self.reconnect_attempts,
            ssl=self.ssl,
        )
        self._manager.client.scheduler.add_job(
            self.node_monitor_task,
            trigger="interval",
            seconds=15,
            max_instances=1,
            id=f"{self.identifier}-{self._manager.client.bot.user.id}-node_monitor_task",
            replace_existing=True,
            coalesce=True,
            next_run_time=get_now_utc() + datetime.timedelta(seconds=15),
        )

    @property
    def trace(self) -> bool:
        """Returns whether the node is being traced or not."""
        if getLogger("PyLav").getEffectiveLevel() < logging.INFO:
            return True
        return self.__cli_flags.logging_level < logging.INFO if self.__cli_flags else False

    async def _unhealthy(self) -> None:
        del self.down_votes
        if self._ws is not None:
            await self.websocket.manual_closure(
                managed_node=self.identifier == self.node_manager.client.bot.user.id and self.websocket is not None
            )
        if self.identifier == self.node_manager.client.bot.user.id:
            await self.node_manager.client.managed_node_controller.restart()
            with contextlib.suppress(Exception):
                await self.close()

    async def node_monitor_task(self) -> None:
        """Monitors the node for health and stability."""
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            if self.websocket and self.websocket._connecting is True:
                return

            try:
                await self.websocket.ping()
                self._logger.trace("Healthy")
            except Exception:  # noqa
                # noinspection PyProtectedMember
                if self.websocket._connecting is True:
                    return
                self._logger.warning("Unhealthy - Triggering a state reset")
                await self._unhealthy()

            playing_players = len(self.playing_players)
            if playing_players == 0:
                return
            if (self.down_votes / playing_players) >= 0.5:
                # noinspection PyProtectedMember
                if self.websocket._connecting is True:
                    return
                await self._unhealthy()

    @property
    def version(self) -> Version | None:
        """The version of the node."""
        return self._version

    @property
    def api_version(self) -> int | None:
        """The API version of the node."""
        return self._api_version

    @property
    def socket_protocol(self) -> str:
        """The protocol used for the socket connection"""
        return "wss" if self._ssl else "ws"

    @property
    def is_ready(self) -> bool:
        """Whether the node is ready or not."""
        return self._ready.is_set() and self.websocket.connected

    @property
    def coordinates(self) -> tuple[int, int]:
        """The coordinates of the node.

        Returns
        -------
        :class:`tuple`
            The coordinates of the node.
        """
        return self._coordinates

    @property
    def managed(self) -> bool:
        """Whether the node is managed or not."""
        return self._managed

    @property
    def config(self) -> node_mocked.NodeMock | node_real.Node:
        """The config of the node."""
        return self._config

    @property
    def identifier(self) -> int:
        """
        The identifier of the :class:`Node`.
        """
        return self._identifier

    @property
    def search_only(self) -> bool:
        """Whether the node is search only or not."""
        return self._search_only

    @property
    def session(self) -> aiohttp.ClientSession:
        """The aiohttp session of the node"""
        return self._session

    @property
    def websocket(self) -> WebSocket:
        """The websocket of the node"""
        return self._ws

    @property
    def node_manager(self) -> NodeManager:
        """The :class:`NodeManager` this node belongs to"""
        return self._manager

    @property
    def port(self) -> int:
        """The port of the node"""
        return self._port

    @property
    def ssl(self) -> bool:
        """Whether the node is using a ssl connection"""
        return self._ssl

    @property
    def connection_protocol(self) -> str:
        """The protocol used for the connection"""
        return "https" if self.ssl else "http"

    @property
    def host(self) -> str:
        """The host of the node"""
        return self._host

    @property
    def region(self) -> str:
        """The region of the node"""
        return self._region

    @property
    def name(self) -> str:
        """The name of the node"""
        return self._name

    @property
    def password(self) -> str:
        """The password of the node"""
        return self._password

    @property
    def resume_timeout(self) -> int:
        """The timeout to use for resuming"""
        return self._resume_timeout

    @property
    def reconnect_attempts(self) -> int:
        """The number of attempts to reconnect to the node"""
        return self._reconnect_attempts

    @property
    def stats(self) -> Stats:
        """The stats of the node"""
        return self._stats

    @stats.setter
    def stats(self, value: Stats) -> None:
        """Sets the stats of the node"""
        if not isinstance(value, Stats):
            raise TypeError("stats must be of type Stats")
        self._stats = value

    @property
    def available(self) -> bool:
        """Returns whether the node is available for requests"""
        return self._ws.connected if self._ws else False

    @property
    def _original_players(self) -> list[Player]:
        """Returns a list of players that were assigned to this node, but were moved due to failover etc"""
        # noinspection PyProtectedMember
        return [p for p in self._manager.client.player_manager.players.values() if p._original_node == self]

    @property
    def players(self) -> list[Player]:
        """Returns a list of all players on this node"""
        return [p for p in self._manager.client.player_manager.players.values() if p.node == self]

    @property
    def playing_players(self) -> list[Player]:
        """Returns a list of all players on this node that are playing"""
        return [p for p in self.players if p.is_active]

    @property
    def connected_players(self) -> list[Player]:
        """Returns a list of all players on this node that are connected"""
        return [p for p in self.players if p.is_connected]

    @property
    def server_connected_players(self) -> int:
        """Returns the number of players on this node that are connected"""
        return self.stats.players if self.stats else self.connected_count

    @property
    def server_playing_players(self) -> int:
        """Returns the number of players on this node that are playing"""
        return self.stats.playing_players if self.stats else self.playing_count

    @property
    def count(self) -> int:
        """Returns the number of players on this node"""
        return len(self.players)

    @property
    def playing_count(self) -> int:
        """Returns the number of players on this node that are playing"""
        return len(self.playing_players)

    @property
    def connected_count(self) -> int:
        """Returns the number of players on this node that are connected"""
        return len(self.connected_players)

    @property
    def penalty(self) -> float:
        """Returns the load-balancing penalty for this node"""
        if not self.available or not self.stats:
            return float("inf")
        return self.stats.penalty.total

    @property
    def session_id(self) -> str:
        """Returns the session id of the node"""
        return self.websocket.session_id if self.websocket else ""

    def down_vote(self, player: Player) -> int:
        """Adds a down vote for this node"""
        if not player.is_active:
            return -1
        self._down_votes[player.guild.id] = 1
        return self.down_votes

    def down_unvote(self, player: Player) -> int:
        """Removes a down vote for this node"""
        if not player.is_active:
            return -1
        self._down_votes.pop(player.guild.id, None)
        return self.down_votes

    @property
    def down_votes(self) -> int:
        """Returns the down votes for this node"""
        return len(set(self._down_votes.keys()))

    def voted(self, player: Player) -> bool:
        """Returns whether a player has voted for this node"""
        return player.guild.id in self._down_votes

    @down_votes.deleter
    def down_votes(self):
        """Clears the down votes for this node"""
        self._down_votes.clear()

    @property
    def can_resume(self) -> bool:
        """Returns whether the node can be resumed"""
        return self._ws.can_resume

    async def penalty_with_region(self, region: str | None) -> float:
        """The penalty for the node, with the region added in"""
        if not region:
            return self.penalty
        return self.penalty + (1.1 ** (0.0025 * await self.region_distance(region)) * 500 - 500)

    def dispatch_event(self, event: PyLavEvent) -> None:
        """|coro|
        Dispatches the given event to all registered hooks.
        Parameters
        ----------
        event: :class:`Event`
            The event to dispatch to the hooks.
        """
        self.node_manager.client.dispatch_event(event)

    def __repr__(self) -> str:
        return (
            f"<Node id={self.identifier} name={self.name} session_id={self.session_id} "
            f"region={self.region} ssl={self.ssl} "
            f"search_only={self.search_only} connected={self.websocket.connected if self._ws else False} "
            f"votes={self.down_votes} "
            f"players={self.server_connected_players} playing={self.server_playing_players}>"
        )

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Node):
            return functools.reduce(
                lambda x, y: x and y,
                map(
                    lambda p, q: p == q,
                    [self.identifier, self.websocket.connected, self.name, self.session_id],
                    [other.identifier, self.websocket.connected, self.name, other.session_id],
                ),
                True,
            )
        elif isinstance(other, (node_real.Node, node_mocked.NodeMock)):
            return self.identifier == other.id
        return NotImplemented

    def __ne__(self, other) -> bool:
        if isinstance(other, Node):
            return self.identifier != other.identifier
        elif isinstance(other, (node_real.Node, node_mocked.NodeMock)):
            return self.identifier != other.id
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.host, self.port))

    @staticmethod
    def parse_loadtrack_response(
        data: JSON_DICT_TYPE,
    ) -> (
        rest_api.ErrorResponse
        | rest_api.EmptyResponse
        | rest_api.PlaylistResponse
        | rest_api.SearchResponse
        | rest_api.TrackResponse
    ):
        """Parses the loadtrack response.
         Parameters
         ----------
         data: LoadTracksResponseT
             The data to parse.
        Returns
         -------
         LavalinkLoadTrackObjects
             Lavalink LoadTrack Response Object
        """

        match data["loadType"]:
            case "error":
                return from_dict(data_class=rest_api.ErrorResponse, data=data)
            case "empty":
                return from_dict(data_class=rest_api.EmptyResponse, data=data)
            case "playlist":
                return from_dict(data_class=rest_api.PlaylistResponse, data=data)
            case "track":
                return from_dict(data_class=rest_api.TrackResponse, data=data)
            case "search":
                return from_dict(data_class=rest_api.SearchResponse, data=data)

    async def get_unsupported_features(self) -> set[str]:
        """|coro|
        Returns the unsupported features of the target node.
        """
        await self.update_features()
        return SUPPORTED_SOURCES.union(SUPPORTED_FEATURES) - self._capabilities

    async def update_features(self) -> set[str]:
        """|coro|
        Updates the features of the target node.
        """
        info = await self.fetch_info()
        self._capabilities.clear()
        self._filters.clear()
        for source in info.sourceManagers:
            self._capabilities.add(source)
        for filterName in info.filters:
            self._filters.add(filterName)
        for plugin in info.plugins:
            match plugin.name:
                case "SponsorBlock-Plugin":
                    self._capabilities.add("sponsorblock")
                case "LavaSearch":
                    self._capabilities.add("lavasearch")
        if self.identifier in PYLAV_NODES:
            self._capabilities.discard("http")
            self._capabilities.discard("local")
        # If not setup says these should be disabled remove them to trick the node to think they are disabled
        if self._capabilities:
            self._capabilities.difference_update(self._disabled_sources)
        return self._capabilities.copy()

    def has_source(self, source: str) -> bool:
        """
        Checks if the target node has the specified source.

        Parameters
        ----------
        source: :class:`str`
            The source to check.

        Returns
        -------
        :class:`bool`
            True if the target node has the specified source, False otherwise.
        """
        return source.lower() in self.sources

    has_capability = has_source

    def has_filter(self, filter_name: str) -> bool:
        """
        Checks if the target node has the specified filter.

        Parameters
        ----------
        filter_name: :class:`str`
            The filter to check.

        Returns
        -------
        :class:`bool`
            True if the target node has the specified filter, False otherwise.
        """
        return filter_name in self._filters

    async def update_disabled_sources(self, sources: set[str]) -> None:
        """
        Updates the disabled sources.

        Returns
        -------
        :class:`None`
        """
        if self.managed or self.identifier in BUNDLED_NODES_IDS_HOST_MAPPING or self.identifier == 31415:
            return
        unsupported = await self.get_unsupported_features()
        currently_disabled = set(await self.config.fetch_disabled_sources())
        unsupported = list(unsupported.union(currently_disabled).union(sources))
        await self.config.update_disabled_sources(unsupported)
        self._disabled_sources = unsupported

    @property
    def capabilities(self) -> set:
        """
        Returns the capabilities of the target node.

        Returns
        -------
        :class:`set`
            The capabilities of the target node.
        """
        return self._capabilities.copy()

    @property
    def disabled_sources(self) -> set:
        """
        Returns the disabled sources of the target node.

        Returns
        -------
        :class:`set`
            The disabled sources of the target node.
        """
        return self._disabled_sources.copy()

    @property
    def sources(self) -> set:
        """
        Returns the sources of the target node.

        Returns
        -------
        :class:`set`
            The sources of the target node.
        """
        return self._capabilities.copy()

    @property
    def supports_spotify(self) -> bool:
        """
        Checks if the target node supports Spotify.

        Returns
        -------
        :class:`bool`
            True if the target node supports Spotify, False otherwise.
        """
        return self.has_source("spotify")

    @property
    def supports_apple_music(self) -> bool:
        """
        Checks if the target node supports Apple Music.

        Returns
        -------
        :class:`bool`
            True if the target node supports Apple Music, False otherwise.
        """
        return self.has_source("applemusic")

    @property
    def supports_getyarn(self) -> bool:
        """
        Checks if the target node supports GetYarn.

        Returns
        -------
        :class:`bool`
            True if the target node supports GetYarn, False otherwise.
        """
        return self.has_source("getyarn.io")

    @property
    def supports_soundgasm(self) -> bool:
        """
        Checks if the target node supports Soundgasm.

        Returns
        -------
        :class:`bool`
            True if the target node supports Soundgasm, False otherwise.
        """
        return self.has_source("soundgasm")

    @property
    def supports_clypit(self) -> bool:
        """
        Checks if the target node supports ClypIt.

        Returns
        -------
        :class:`bool`
            True if the target node supports ClypIt, False otherwise.
        """
        return self.has_source("clypit")

    @property
    def supports_speak(self) -> bool:
        """
        Checks if the target node supports speak source.

        Returns
        -------
        :class:`bool`
            True if the target node supports speak, False otherwise.
        """
        return self.has_source("speak")

    @property
    def supports_tts(self) -> bool:
        """
        Checks if the target node supports Google Cloud TTS.

        Returns
        -------
        :class:`bool`
            True if the target node supports Google Cloud TTS, False otherwise.
        """
        return self.has_capability("gcloud-tts")

    @property
    def supports_pornhub(self) -> bool:
        """
        Checks if the target node supports PornHub.

        Returns
        -------
        :class:`bool`
            True if the target node supports PornHub, False otherwise.
        """
        return self.has_source("pornhub")

    @property
    def supports_reddit(self) -> bool:
        """
        Checks if the target node supports Reddit.

        Returns
        -------
        :class:`bool`
            True if the target node supports Reddit, False otherwise.
        """
        return self.has_source("reddit")

    @property
    def supports_ocremix(self) -> bool:
        """
        Checks if the target node supports OCRemix.

        Returns
        -------
        :class:`bool`
            True if the target node supports OCRemix, False otherwise.
        """
        return self.has_source("ocremix")

    @property
    def supports_mixcloud(self) -> bool:
        """
        Checks if the target node supports Mixcloud.

        Returns
        -------
        :class:`bool`
            True if the target node supports Mixcloud, False otherwise.
        """
        return self.has_source("mixcloud")

    @property
    def supports_tiktok(self) -> bool:
        """
        Checks if the target node supports TikTok.

        Returns
        -------
        :class:`bool`
            True if the target node supports TikTok, False otherwise.
        """
        return self.has_source("tiktok")

    @property
    def supports_youtube(self) -> bool:
        """
        Checks if the target node supports YouTube.

        Returns
        -------
        :class:`bool`
            True if the target node supports YouTube, False otherwise.
        """
        return self.has_source("youtube")

    @property
    def supports_bandcamp(self) -> bool:
        """
        Checks if the target node supports Bandcamp.

        Returns
        -------
        :class:`bool`
            True if the target node supports Bandcamp, False otherwise.
        """
        return self.has_source("bandcamp")

    @property
    def supports_soundcloud(self) -> bool:
        """
        Checks if the target node supports SoundCloud.

        Returns
        -------
        :class:`bool`
            True if the target node supports SoundCloud, False otherwise.
        """
        return self.has_source("soundcloud")

    @property
    def supports_twitch(self) -> bool:
        """
        Checks if the target node supports Twitch.

        Returns
        -------
        :class:`bool`
            True if the target node supports Twitch, False otherwise.
        """
        return self.has_source("twitch")

    @property
    def supports_deezer(self) -> bool:
        """
        Checks if the target node supports Deezer.

        Returns
        -------
        :class:`bool`
            True if the target node supports Deezer, False otherwise.
        """
        return self.has_source("deezer")

    @property
    def supports_yandex_music(self) -> bool:
        """
        Checks if the target node supports Yandex Music.

        Returns
        -------
        :class:`bool`
            True if the target node supports Yandex Music, False otherwise.
        """
        return self.has_source("yandexmusic")

    @property
    def supports_vimeo(self) -> bool:
        """
        Checks if the target node supports Vimeo.

        Returns
        -------
        :class:`bool`
            True if the target node supports Vimeo, False otherwise.
        """
        return self.has_source("vimeo")

    @property
    def supports_http(self) -> bool:
        """
        Checks if the target node supports HTTP.

        Returns
        -------
        :class:`bool`
            True if the target node supports HTTP, False otherwise.
        """
        return self.has_source("http")

    @property
    def supports_local(self) -> bool:
        """
        Checks if the target node supports local files.

        Returns
        -------
        :class:`bool`
            True if the target node supports local files, False otherwise.
        """
        return self.has_source("local")

    @property
    def supports_sponsorblock(self) -> bool:
        """
        Checks if the target node supports SponsorBlock.

        Returns
        -------
        :class:`bool`
            True if the target node supports SponsorBlock, False otherwise.
        """
        return self.has_capability("sponsorblock")

    @property
    def supports_lavasearch(self) -> bool:
        """
        Checks if the target node supports LavaSearch.

        Returns
        -------
        :class:`bool`
            True if the target node supports LavaSearch, False otherwise.
        """
        return self.has_capability("lavasearch")

    async def close(self) -> None:
        """
        Closes the target node.
        """
        if self.websocket is not None:
            await self.websocket.close()
        await self.session.close()
        with contextlib.suppress(JobLookupError):
            self.node_manager.client.scheduler.remove_job(
                job_id=f"{self.identifier}-{self._manager.client.bot.user.id}-node_monitor_task"
            )

    async def wait_until_ready(self, timeout: float | None = None):
        """Waits until the target node is ready."""
        await asyncio.wait_for(self._ready.wait(), timeout=timeout)

    async def region_distance(self, region: str) -> float:
        """
        Returns the numeric representation of the distance between the target node and the given region.

        Parameters
        ----------
        region : :class:`str`
            The region to get the distance to.

        Returns
        -------
        :class:`float`
            The numeric representation of the distance between the target node and the given region.
        """
        coordinates = REGION_TO_COUNTRY_COORDINATE_MAPPING.get(region)

        return distance(*self.coordinates, *coordinates) if (coordinates and self.coordinates) else float("inf")

    async def get_track_from_cache(
        self, query: Query, first: bool = False
    ) -> rest_api.PlaylistResponse | rest_api.SearchResponse | rest_api.TrackResponse | None:
        """Gets a query from the query cache."""
        response = await self.node_manager.client.query_cache_manager.fetch_query(query)
        if not response:
            return
        load_type = "playlist" if query.is_playlist or query.is_album else "search" if query.is_search else "track"
        kwargs = {"tracks": True}
        match load_type:
            case "playlist":
                kwargs["info"] = True
                kwargs["pluginInfo"] = True
                kwargs["name"] = True

        cached_query = await response.fetch_bulk(**kwargs)
        if cached_query is None:
            return
        if tracks := cached_query["tracks"]:
            try:
                if tracks and first:
                    tracks = [tracks[0]]
            except Exception:  # noqa
                tracks = []
                load_type = "error"

            data = {"loadType": load_type, "data": None}
            match data["loadType"]:
                case "playlist":
                    data["data"] = {
                        "info": cached_query["info"] or {"name": cached_query["name"] or "", "selectedTrack": 0},
                        "pluginInfo": cached_query["pluginInfo"],
                        "tracks": tracks,
                    }
                case "search":
                    data["data"] = tracks
                case "track":
                    data["data"] = tracks[0]
                case "empty":
                    data["data"] = None
                case "error":
                    data["data"] = {"cause": "No tracks returned", "severity": "common", "message": "No tracks found"}
            response = self.parse_loadtrack_response(data)
            return response

    @property
    def base_url(self) -> URL:
        """Returns the base URL of the target node."""
        return URL(f"{self.connection_protocol}://{self.host}:{self.port}")

    @property
    def base_api_url(self) -> URL:
        """Returns the base API URL of the target node."""
        return self.base_url / f"v{self.api_version}"

    @property
    def base_ws_url(self) -> URL:
        """Returns the base WebSocket URL of the target node."""
        return self.base_api_url.with_scheme(self.socket_protocol)

    # ENDPOINTS
    def get_endpoint_websocket(self) -> URL:
        """Returns the WebSocket endpoint of the target node."""
        return self.base_ws_url / "websocket"

    def get_endpoint_info(self) -> URL:
        """Returns the info endpoint of the target node."""
        return self.base_api_url / "info"

    def get_endpoint_session_players(self) -> URL:
        """Returns the session players endpoint of the target node."""
        return self.get_endpoint_session() / "players"

    def get_endpoint_session_player_by_guild_id(self, guild_id: int) -> URL:
        """Returns the session player endpoint of the target node for the given guild ID."""
        return self.get_endpoint_session_players() / f"{guild_id}"

    def get_endpoint_session(self) -> URL:
        """Returns the session endpoint of the target node."""
        return self.base_api_url / "sessions" / self.session_id

    def get_endpoint_loadtracks(self) -> URL:
        """Returns the loadtracks endpoint of the target node."""
        return self.base_api_url / "loadtracks"

    def get_endpoint_loadseach(self) -> URL:
        """Returns the loadsearch endpoint of the target node."""
        return self.base_api_url / "loadsearch"

    def get_endpoint_decodetrack(self) -> URL:
        """Returns the decodetrack endpoint of the target node."""
        return self.base_api_url / "decodetrack"

    def get_endpoint_decodetracks(self) -> URL:
        """Returns the decodetracks endpoint of the target node."""
        return self.base_api_url / "decodetracks"

    def get_endpoint_stats(self) -> URL:
        """Returns the stats endpoint of the target node."""
        return self.base_api_url / "stats"

    def get_endpoint_routeplanner_status(self) -> URL:
        """Returns the routeplanner status endpoint of the target node."""
        return self.base_api_url / "routeplanner" / "status"

    def get_endpoint_routeplanner_free_address(self) -> URL:
        """Returns the routeplanner free address endpoint of the target node."""
        return self.base_api_url / "routeplanner" / "free" / "address"

    def get_endpoint_routeplanner_free_all(self) -> URL:
        """Returns the routeplanner free all endpoint of the target node."""
        return self.base_api_url / "routeplanner" / "free" / "all"

    def get_endpoint_session_player_sponsorblock_categories(self, guild_id: int) -> URL:
        """Returns the session player sponsorblock categories endpoint of the target node for the given guild ID."""
        return self.get_endpoint_session_player_by_guild_id(guild_id) / "sponsorblock" / "categories"

    def get_endpoint_version(self) -> URL:
        """Returns the version endpoint of the target node."""
        return self.base_url / "version"

    # REST API - Direct calls
    async def fetch_session_players(self) -> list[rest_api.LavalinkPlayer] | HTTPException:
        """|coro|
        Gets all players associated with the target node.

        Returns
        -------
        list[rest_api.LavalinkPlayer]
            A list of all players associated with the target node.
        """
        async with self._session.get(
            self.get_endpoint_session_players(),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return [from_dict(data_class=rest_api.LavalinkPlayer, data=t) for t in await res.json(loads=json.loads)]
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to get session players: %d %s", failure.status, failure.message)
            return HTTPException(failure)

    async def fetch_session_player(self, guild_id: int) -> rest_api.LavalinkPlayer | HTTPException:
        """|coro|
        Gets the player associated with the target node and the given guild ID.
        """
        async with self._session.get(
            self.get_endpoint_session_player_by_guild_id(guild_id=guild_id),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=rest_api.LavalinkPlayer, data=await res.json(loads=json.loads))
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to get session player: %d %s", failure.status, failure.message)
            return HTTPException(failure)

    async def patch_session_player(
        self, guild_id: int, no_replace: bool = False, payload: JSON_DICT_TYPE = None
    ) -> rest_api.LavalinkPlayer | HTTPException:
        """|coro|
        Updates the player associated with the target node and the given guild ID.
        """
        async with self._session.patch(
            self.get_endpoint_session_player_by_guild_id(guild_id=guild_id),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"noReplace": "true" if no_replace else "false", "trace": "true" if self.trace else "false"},
            json=payload,
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=rest_api.LavalinkPlayer, data=await res.json(loads=json.loads))
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to patch session player: %d %s", failure.status, failure.message)
            return HTTPException(failure)

    async def delete_session_player(self, guild_id: int) -> None | HTTPException:
        """|coro|
        Deletes the player associated with the target node and the given guild ID.
        """
        async with self._session.delete(
            self.get_endpoint_session_player_by_guild_id(guild_id=guild_id),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE or res.status in [404]:
                return
            response = await res.json(loads=json.loads)
            failure = from_dict(data_class=LavalinkError, data=response)
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to delete session player: %d %s", failure.status, failure.message)
            return HTTPException(failure)

    async def get_session_player_sponsorblock_categories(self, guild_id: int) -> list[str] | HTTPException:
        """|coro|
        Gets the sponsorblock categories for the player associated with the target node and the given guild ID.
        """
        async with self._session.get(
            self.get_endpoint_session_player_sponsorblock_categories(guild_id=guild_id),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return await res.json(loads=json.loads)
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace(
                "Failed to get session player sponsorblock categories: %d %s", failure.status, failure.message
            )
            return HTTPException(failure)

    async def put_session_player_sponsorblock_categories(
        self, guild_id: int, categories: list[str]
    ) -> None | HTTPException:
        """|coro|
        Sets the sponsorblock categories for the player associated with the target node and the given guild ID.
        """
        async with self._session.put(
            self.get_endpoint_session_player_sponsorblock_categories(guild_id=guild_id),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            json=categories,
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace(
                "Failed to put session player sponsorblock categories: %d %s", failure.status, failure.message
            )
            return HTTPException(failure)

    async def delete_session_player_sponsorblock_categories(self, guild_id: int) -> None | HTTPException:
        """|coro|
        Deletes the sponsorblock categories for the player associated with the target node and the given guild ID.
        """
        async with self._session.delete(
            self.get_endpoint_session_player_sponsorblock_categories(guild_id=guild_id),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace(
                "Failed to delete session player sponsorblock categories: %d %s", failure.status, failure.message
            )
            return HTTPException(failure)

    async def patch_session(self, payload: JSON_DICT_TYPE) -> None | HTTPException:
        """|coro|
        Patches the session associated with the target node.
        """
        async with self._session.patch(
            self.get_endpoint_session(),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            json=payload,
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to delete session player: %d %s", failure.status, failure.message)
            return HTTPException(failure)

    async def fetch_loadtracks(self, query: Query) -> rest_api.LoadTrackResponses:
        """|coro|
        Fetches the loadtracks response from the target node.
        """
        if not self.available or not self.has_source(query.requires_capability):
            return dataclasses.replace(EMPTY_RESPONSE)

        async with self._session.get(
            self.get_endpoint_loadtracks(),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"identifier": query.query_identifier},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                result = await res.json(loads=json.loads)
                self._logger.trace("Loaded track: %s response: %s", query, result)
                response = self.parse_loadtrack_response(result)
                asyncio.create_task(self.node_manager.client.query_cache_manager.add_query(query, response))
                self._manager.client.dispatch_event(LavalinkLoadtracksEvent(node=self, response=response))
                return response
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to load track: %d %s", failure.status, failure.message)
            return HTTPException(failure)

    async def fetch_loadsearch(
        self, query: Query
    ) -> rest_api.LoadSearchResponses | LavalinkError | HTTPException | None:
        if not self.available or not self.has_source(query.requires_capability):
            return None

        async with self._session.get(
            self.get_endpoint_loadseach(),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"query": query.query_identifier, "trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                if res.status == 204:
                    return None
                result = await res.json(loads=json.loads)
                self._logger.trace("Loaded Search Result: %s response: %s", query, result)
                response = from_dict(data_class=rest_api.LoadSearchResponses, data=result)
                asyncio.create_task(self.node_manager.client.query_cache_manager.add_query(query, response))
                self._manager.client.dispatch_event(LavalinkLoadSearchEvent(node=self, response=response))
                return response
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to load track: %d %s", failure.status, failure.message)
            return HTTPException(failure)

    async def fetch_decodetrack(
        self, encoded_track: str, timeout: aiohttp.ClientTimeout | object = sentinel, raise_on_failure: bool = True
    ) -> Track | HTTPException:
        """|coro|
        Fetches the decodetrack response from the target node.
        """
        async with self._manager._client.cached_session.get(
            self.get_endpoint_decodetrack(),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"encodedTrack": encoded_track, "trace": "true" if self.trace else "false"},
            timeout=timeout,
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=Track, data=await res.json(loads=json.loads))
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to decode track: %d %s", failure.status, failure.message)
            if raise_on_failure:
                raise HTTPException(failure)
            return HTTPException(failure)

    async def post_decodetracks(
        self, encoded_tracks: list[str], raise_on_failure: bool = False
    ) -> list[Track] | HTTPException:
        """|coro|
        Posts the decodetracks response from the target node.
        """
        async with self._manager._client.cached_session.post(
            self.get_endpoint_decodetracks(),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            json=encoded_tracks,
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return [from_dict(data_class=Track, data=t) for t in await res.json(loads=json.loads)]
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to decode tracks: %d %s", failure.status, failure.message)
            if raise_on_failure:
                raise HTTPException(failure)
            return HTTPException(failure)

    async def fetch_info(self, raise_on_error: bool = False) -> rest_api.LavalinkInfo | HTTPException:
        """|coro|
        Fetches the info response from the target node.
        """
        async with self._session.get(
            self.get_endpoint_info(),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=rest_api.LavalinkInfo, data=await res.json(loads=json.loads))
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                if raise_on_error:
                    raise UnauthorizedException(failure)
                return UnauthorizedException(failure)
            self._logger.trace("Failed to get info: %d %s", failure.status, failure.message)
            if raise_on_error:
                raise HTTPException(failure)
            return HTTPException(failure)

    def _process_version_from_headers(self, headers: CIMultiDictProxy[str]) -> Version:
        self._api_version = int(headers.get("Lavalink-API-Version") or MAX_SUPPORTED_API_MAJOR_VERSION)
        version_str = f"{self._api_version}.9999.9999"
        return Version(version_str)

    async def fetch_stats(self, raise_on_error: bool = False) -> websocket_responses.Stats | HTTPException:
        """|coro|
        Fetches the stats response from the target node.
        """
        async with self._session.get(
            self.get_endpoint_stats(),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=rest_api.Stats, data=await res.json(loads=json.loads))
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                if raise_on_error:
                    raise UnauthorizedException(failure)
                return HTTPException(failure)
            self._logger.trace("Failed to get stats: %d %s", failure.status, failure.message)
            if raise_on_error:
                raise HTTPException(failure)
            return HTTPException(failure)

    async def fetch_version(self, raise_on_error: bool = False) -> Version | HTTPException:
        """|coro|
        Fetches the version response from the target node.
        """
        async with self._session.get(
            self.get_endpoint_version(),
            headers={
                "Authorization": self.password,
                "Content-Type": "text/plain",
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                text = await res.text()
                version_from_header = self._process_version_from_headers(res.headers)
                return parse(text) if SEMANTIC_VERSIONING.match(text) else version_from_header
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                if raise_on_error:
                    raise UnauthorizedException(failure)
                return HTTPException(failure)
            self._logger.trace("Failed to get version: %d %s", failure.status, failure.message)
            if raise_on_error:
                raise HTTPException(failure)
            return HTTPException(failure)

    async def fetch_routeplanner_status(self) -> RoutePlannerStart | HTTPException:
        """|coro|
        Fetches the routeplanner status response from the target node.
        """
        async with self._session.get(
            self.get_endpoint_routeplanner_status(),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                data = await res.json(loads=json.loads)
                data["type"] = data["class"]
                del data["class"]
                return from_dict(data_class=RoutePlannerStart, data=data)
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to get routeplanner status: %d %s", failure.status, failure.message)
            return HTTPException(failure)

    async def post_routeplanner_free_address(self, address: str) -> None | HTTPException:
        """|coro|
        Frees the given address from the routeplanner.
        """
        async with self._session.post(
            self.get_endpoint_routeplanner_free_address(),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            json={"address": address},
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to free routeplanner address: %d %s", failure.status, failure.message)
            return HTTPException(failure)

    async def post_routeplanner_free_all(self) -> None | HTTPException:
        """|coro|
        Frees all addresses from the routeplanner.
        """
        async with self._session.post(
            self.get_endpoint_routeplanner_free_all(),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return
            failure = from_dict(data_class=LavalinkError, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException(failure)
            self._logger.trace("Failed to free all routeplanner addresses: %d %s", failure.status, failure.message)
            return HTTPException(failure)

    # REST API - Wrappers

    async def fetch_node_version(self) -> Version:
        """|coro|
        Fetches the version response from the target node.
        """
        self._version = await self.fetch_version(raise_on_error=True)
        return self._version

    async def fetch_api_version(self) -> None:
        """|coro|
        Fetches the API version response from the target node.
        """
        if self.version is None:
            await self.fetch_node_version()

    async def get_guild_player(self, guild_id: int) -> rest_api.LavalinkPlayer:
        """|coro|
        Fetches the player for the given guild ID.
        """
        async with self._session.get(
            self.get_endpoint_session_player_by_guild_id(guild_id=guild_id),
            headers={
                "Authorization": self.password,
                "Client-Name": f"PyLav/{self.node_manager.client.lib_version}",
                "App-Id": self.node_manager.client._user_id,
            },
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=rest_api.LavalinkPlayer, data=await res.json(loads=json.loads))
            if res.status in [401, 403]:
                raise UnauthorizedException
        raise ValueError(f"Server returned an unexpected return code: {res.status}")

    async def get_track(
        self, query: Query, first: bool = False, bypass_cache: bool = False, sleep: bool = False
    ) -> rest_api.LoadTrackResponses:
        """|coro|
        Gets all tracks associated with the given query.

        Parameters
        ----------
        query: :class:`Query`
            The query to perform a search for.
        first: :class:`bool`
            Whether to return the first result or all results.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.
        sleep: :class:`bool`
            Whether to sleep for 1 second before returning the response.
        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response object
        """
        if not bypass_cache:
            if cached_entry := await self.get_track_from_cache(query=query, first=first):
                return cached_entry
        if (
            self.node_manager.client.local_tracks_cache.is_ready
            and query.is_local
            and f"{query._query}" in self.node_manager.client.local_tracks_cache.path_to_track
        ):
            return self.parse_loadtrack_response(
                {
                    "loadType": "track",
                    "data": self.node_manager.client.local_tracks_cache.path_to_track[f"{query._query}"],
                }
            )
        response = await self.fetch_loadtracks(query=query)
        if sleep:
            await asyncio.sleep(0.05)
        if isinstance(response, HTTPException):
            return response
        if first:
            match response.loadType:
                case "track":
                    return response
                case "search":
                    return rest_api.TrackResponse(loadType="track", data=response.data[0])
                case "playlist":
                    return rest_api.TrackResponse(loadType="track", data=response.data.tracks[0])
        return response

    async def get_lavasearch_collection(
        self,
        query: Query,
        bypass_cache: bool = False,
        sleep: bool = False,
        filter: Literal["tracks", "albums", "artists", "playlists"] | None = None,
    ) -> rest_api.LoadSearchResponses | list[PlaylistData] | list[Track] | None:
        """|coro|
        Gets all tracks associated with the given query.

        Parameters
        ----------
        query: :class:`Query`
            The query to perform a search for.
        filter: Optional[Literal["tracks" , "albums", "artists", "playlists"]]
            Whether to filter the response to a specific type.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.
        sleep: :class:`bool`
            Whether to sleep for 1 second before returning the response.
        Returns
        -------
        Optional[rest_api.LoadSearchResponses | list[PlaylistData] | list[Track]]
            Lavalink LoadSearch Response object
        """
        if not bypass_cache:
            if cached_entry := await self.get_track_from_cache(query=query):
                return cached_entry
        response = await self.fetch_loadsearch(query=query)
        if sleep:
            await asyncio.sleep(0.05)
        if isinstance(response, type(None)):
            return
        match filter:
            case "tracks":
                return response.tracks
            case "albums":
                return response.albums
            case "artists":
                return response.artists
            case "playlists":
                return response.playlists
            case _:
                return response

    async def search_youtube_music(self, query: str, bypass_cache: bool = False) -> rest_api.LoadTrackResponses:
        """|coro|
        Gets the query from YouTube music.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.
        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response Object
        """
        return await self.get_track(await self._query_cls.from_string(f"ytmsearch:{query}"), bypass_cache=bypass_cache)

    async def search_youtube(self, query: str, bypass_cache: bool = False) -> rest_api.LoadTrackResponses:
        """|coro|
        Gets the query from YouTube music.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.
        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response Object
        """
        return await self.get_track(await self._query_cls.from_string(f"ytsearch:{query}"), bypass_cache=bypass_cache)

    async def search_soundcloud(self, query: str, bypass_cache: bool = False) -> rest_api.LoadTrackResponses:
        """|coro|
        Gets the query from Soundcloud.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.
        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response Object
        """
        return await self.get_track(await self._query_cls.from_string(f"scsearch:{query}"), bypass_cache=bypass_cache)

    async def search_spotify(self, query: str, bypass_cache: bool = False) -> rest_api.LoadTrackResponses:
        """|coro|
        Gets the query from Spotify.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.
        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response Object
        """
        return await self.get_track(await self._query_cls.from_string(f"spsearch:{query}"), bypass_cache=bypass_cache)

    async def search_apple_music(self, query: str, bypass_cache: bool = False) -> rest_api.LoadTrackResponses:
        """|coro|
        Gets the query from Apple Music.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.

        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response Object
        """
        return await self.get_track(await self._query_cls.from_string(f"amsearch:{query}"), bypass_cache=bypass_cache)

    async def search_deezer(self, query: str, bypass_cache: bool = False) -> rest_api.LoadTrackResponses:
        """|coro|
        Gets the query from Deezer.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.

        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response Object
        """
        return await self.get_track(await self._query_cls.from_string(f"dzsearch:{query}"), bypass_cache=bypass_cache)

    async def search_yandex(self, query: str, bypass_cache: bool = False) -> rest_api.LoadTrackResponses:
        """|coro|
        Gets the query from Yandex Music.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.

        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response Object
        """
        return await self.get_track(await self._query_cls.from_string(f"ymsearch:{query}"), bypass_cache=bypass_cache)

    async def get_query_speak(self, query: str, bypass_cache: bool = False) -> rest_api.LoadTrackResponses:
        """|coro|
        Gets the query for speak.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.
        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response Object
        """
        return await self.get_track(
            await self._query_cls.from_string(f"speak:{query[:200]}"), bypass_cache=bypass_cache
        )

    async def get_query_localfiles(
        self,
        query: str,
        bypass_cache: bool = True,
    ) -> rest_api.LoadTrackResponses:
        """|coro|
        Gets the query from Localfiles.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.

        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response Object
        """
        return await self.get_track(await self._query_cls.from_string(query), bypass_cache=bypass_cache)

    async def get_lavasearch(self, query: str, bypass_cache: bool = False) -> rest_api.LoadSearchResponses:
        """|coro|
        Gets the query from LavaSearch.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.

        Returns
        -------
        LavalinkLoadSearchObjects
            Lavalink LoadSearch Response Object
        """
        return await self.get_lavasearch_collection(
            await self._query_cls.from_string(f"lavasearch:{query}"), bypass_cache=bypass_cache
        )

    def get_filter_payload(
        self,
        *,
        player: Player,
        volume: Volume = None,
        equalizer: Equalizer = None,
        karaoke: Karaoke = None,
        timescale: Timescale = None,
        tremolo: Tremolo = None,
        vibrato: Vibrato = None,
        rotation: Rotation = None,
        distortion: Distortion = None,
        low_pass: LowPass = None,
        channel_mix: ChannelMix = None,
        reset_no_set: bool = False,
        reset: bool = False,
        pluginFilters: dict[str, Echo | None] = None,
    ) -> JSON_DICT_TYPE:
        """Gets the filter payload."""
        if reset:
            return {}
        if pluginFilters is None:
            pluginFilters = {}
        payload = {}
        if self.has_filter("volume"):
            self._get_filter_payload_volume(payload, volume)
        if self.has_filter("equalizer"):
            self._get_filter_payload_equalizer(equalizer, payload, player, reset_no_set)
        if self.has_filter("karaoke"):
            self._get_filter_payload_karaoke(karaoke, payload, player, reset_no_set)
        if self.has_filter("timescale"):
            self._get_filter_payload_timescale(payload, player, reset_no_set, timescale)
        if self.has_filter("tremolo"):
            self._get_filter_payload_tremolo(payload, player, reset_no_set, tremolo)
        if self.has_filter("vibrato"):
            self._get_filter_payload_vibrato(payload, player, reset_no_set, vibrato)
        if self.has_filter("rotation"):
            self._get_filter_payload_rotation(payload, player, reset_no_set, rotation)
        if self.has_filter("distortion"):
            self._get_filter_payload_distortion(distortion, payload, player, reset_no_set)
        if self.has_filter("lowPass"):
            self._get_filter_payload_low_pass(low_pass, payload, player, reset_no_set)
        if self.has_filter("channelMix"):
            self._get_filter_payload_channel_mix(channel_mix, payload, player, reset_no_set)
        if self.has_filter("echo"):
            echo = pluginFilters.get("echo")
            self._get_filter_payload_echo(echo, payload, player, reset_no_set)

        return payload

    @staticmethod
    def _get_filter_payload_volume(payload: JSON_DICT_TYPE, volume: Volume) -> None:
        if volume:
            payload["volume"] = volume.get()

    @staticmethod
    def _get_filter_payload_echo(echo: Echo, payload: JSON_DICT_TYPE, player: Player, reset_no_set: bool) -> None:
        if "pluginFilters" not in payload:
            payload["pluginFilters"] = {}
        if echo:
            payload["pluginFilters"]["echo"] = echo.get()
        elif not reset_no_set and player.echo:
            payload["pluginFilters"]["echo"] = player.echo.get()

    @staticmethod
    def _get_filter_payload_channel_mix(
        channel_mix: ChannelMix, payload: JSON_DICT_TYPE, player: Player, reset_no_set: bool
    ) -> None:
        if channel_mix:
            payload["channelMix"] = channel_mix.get()
        elif not reset_no_set and player.channel_mix:
            payload["channelMix"] = player.channel_mix.get()

    @staticmethod
    def _get_filter_payload_low_pass(
        low_pass: LowPass, payload: JSON_DICT_TYPE, player: Player, reset_no_set: bool
    ) -> None:
        if low_pass:
            payload["lowPass"] = low_pass.get()
        elif not reset_no_set and player.low_pass:
            payload["lowPass"] = player.low_pass.get()

    @staticmethod
    def _get_filter_payload_distortion(
        distortion: Distortion, payload: JSON_DICT_TYPE, player: Player, reset_no_set: bool
    ) -> None:
        if distortion:
            payload["distortion"] = distortion.get()
        elif not reset_no_set and player.distortion:
            payload["distortion"] = player.distortion.get()

    @staticmethod
    def _get_filter_payload_rotation(
        payload: JSON_DICT_TYPE, player: Player, reset_no_set: bool, rotation: Rotation
    ) -> None:
        if rotation:
            payload["rotation"] = rotation.get()
        elif not reset_no_set and player.rotation:
            payload["rotation"] = player.rotation.get()

    @staticmethod
    def _get_filter_payload_vibrato(
        payload: JSON_DICT_TYPE, player: Player, reset_no_set: bool, vibrato: Vibrato
    ) -> None:
        if vibrato:
            payload["vibrato"] = vibrato.get()
        elif not reset_no_set and player.vibrato:
            payload["vibrato"] = player.vibrato.get()

    @staticmethod
    def _get_filter_payload_tremolo(
        payload: JSON_DICT_TYPE, player: Player, reset_no_set: bool, tremolo: Tremolo
    ) -> None:
        if tremolo:
            payload["tremolo"] = tremolo.get()
        elif not reset_no_set and player.timescale:
            payload["timescale"] = player.timescale.get()

    @staticmethod
    def _get_filter_payload_timescale(
        payload: JSON_DICT_TYPE, player: Player, reset_no_set: bool, timescale: Timescale
    ) -> None:
        if timescale:
            payload["timescale"] = timescale.get()
        elif not reset_no_set and player.timescale:
            payload["timescale"] = player.timescale.get()

    @staticmethod
    def _get_filter_payload_karaoke(
        karaoke: Karaoke, payload: JSON_DICT_TYPE, player: Player, reset_no_set: bool
    ) -> None:
        if karaoke:
            payload["karaoke"] = karaoke.get()
        elif not reset_no_set and player.karaoke:
            payload["karaoke"] = player.karaoke.get()

    @staticmethod
    def _get_filter_payload_equalizer(
        equalizer: Equalizer, payload: JSON_DICT_TYPE, player: Player, reset_no_set: bool
    ) -> None:
        if equalizer:
            payload["equalizer"] = equalizer.get()
        elif not reset_no_set and player.equalizer:
            payload["equalizer"] = player.equalizer.get()

    async def filters(
        self,
        *,
        player: Player,
        volume: Volume = None,
        equalizer: Equalizer = None,
        karaoke: Karaoke = None,
        timescale: Timescale = None,
        tremolo: Tremolo = None,
        vibrato: Vibrato = None,
        rotation: Rotation = None,
        distortion: Distortion = None,
        low_pass: LowPass = None,
        channel_mix: ChannelMix = None,
        echo: Echo = None,
    ) -> None:
        """|coro|
        Set the filters for a player.
        """
        payload = self.get_filter_payload(
            player=self.node_manager.client.player_manager.get(player.guild.id),
            volume=volume,
            equalizer=equalizer,
            karaoke=karaoke,
            timescale=timescale,
            tremolo=tremolo,
            vibrato=vibrato,
            rotation=rotation,
            distortion=distortion,
            low_pass=low_pass,
            channel_mix=channel_mix,
            pluginFilters=dict(echo=echo),
        )
        player.add_voice_to_payload(payload)
        await self.patch_session_player(guild_id=player.guild.id, payload={"filters": payload})
