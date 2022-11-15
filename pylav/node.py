from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import datetime
import functools
import logging
import pathlib
import re
import typing
from typing import TYPE_CHECKING
from uuid import uuid4

import aiohttp
import ujson
from aiohttp.helpers import sentinel
from apscheduler.jobstores.base import JobLookupError
from dacite import from_dict
from discord.utils import utcnow
from expiringdict import ExpiringDict
from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

from pylav._logging import getLogger
from pylav.constants import (
    BUNDLED_NODES_IDS_HOST_MAPPING,
    PYLAV_NODES,
    REGION_TO_COUNTRY_COORDINATE_MAPPING,
    SUPPORTED_FEATURES,
    SUPPORTED_SOURCES,
)
from pylav.endpoints.response_objects import (
    LavalinkErrorResponseObject,
    LavalinkInfoObject,
    LavalinkLoadFailedObject,
    LavalinkLoadTrackObjects,
    LavalinkNoMatchesObject,
    LavalinkPlayerObject,
    LavalinkPlaylistLoadedObject,
    LavalinkSearchResultObject,
    LavalinkStatsOpObject,
    LavalinkTrackLoadedObject,
    LavalinkTrackObject,
    PlaylistInfoObject,
    RoutePlannerStatusResponseObject,
)
from pylav.events import Event
from pylav.exceptions import HTTPError, Unauthorized, UnsupportedNodeAPI
from pylav.filters import (
    ChannelMix,
    Distortion,
    Echo,
    Equalizer,
    Karaoke,
    LowPass,
    Rotation,
    Timescale,
    Vibrato,
    Volume,
)
from pylav.filters.tremolo import Tremolo
from pylav.location import distance
from pylav.sql.models import NodeModel, NodeModelMock
from pylav.track_encoding import decode_track
from pylav.types import FiltersT, LoadTracksResponseT, RestPatchPlayerPayloadT, RestPatchSessionPayloadT
from pylav.utils import AsyncIter

if TYPE_CHECKING:
    from pylav.node_manager import NodeManager
    from pylav.player import Player
    from pylav.query import Query
    from pylav.websocket import WebSocket

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLavPlayer", pathlib.Path(__file__))
except ImportError:

    def _(string: str) -> str:
        return string


NO_MATCHES = LavalinkNoMatchesObject(
    loadType="NO_MATCHES", tracks=[], playlistInfo=PlaylistInfoObject(name="", selectedTrack=-1)
)
SNAPSHOT_REGEX = re.compile(r"^(?P<commit>.*?)-SNAPSHOT$")
GOOD_RESPONSE_RANGE = range(200, 299)


class Penalty:
    """Represents the penalty of the stats of a Node"""

    __slots__ = ("_stats",)

    def __init__(self, stats: Stats):
        self._stats = stats

    @property
    def player_penalty(self) -> int:
        """The penalty of the players playing on the node.

        This is the number of players playing in the node.
        """
        return self._stats.playing_players

    @property
    def cpu_penalty(self) -> float:
        """The penalty of the cpu load of the node"""
        return 1.05 ** (100 * self._stats.system_load) * 10 - 10

    @property
    def null_frame_penalty(self) -> float | int:
        """The penalty of the nulled frames of the node"""
        null_frame_penalty = 0
        if self._stats.frames_nulled != -1:
            null_frame_penalty = (1.03 ** (500 * (self._stats.frames_nulled / 3000))) * 300 - 300
            null_frame_penalty *= 2
        return null_frame_penalty

    @property
    def deficit_frame_penalty(self) -> float | int:
        """The penalty of the deficit frames of the node"""
        return (
            1.03 ** (500 * (self._stats.frames_deficit / 3000)) * 600 - 600 if self._stats.frames_deficit != -1 else 0
        )

    @property
    def total(self) -> float:
        """The total penalty of the node.

        This is the sum of the penalties of the node.
        """
        return (
            self.player_penalty
            + self.cpu_penalty
            + self.null_frame_penalty
            + self.deficit_frame_penalty
            + self._stats._node.down_votes * 100
        )

    def __repr__(self):
        return f"<Penalty player={self.player_penalty} cpu={self.cpu_penalty} null_frame={self.null_frame_penalty} deficit_frame={self.deficit_frame_penalty} votes={self._stats._node.down_votes * 100} total={self.total}>"


class Stats:
    """Represents the stats of Lavalink node"""

    __slots__ = (
        "_node",
        "_data",
        "_penalty",
        "_memory",
        "_cpu",
        "_frame_stats",
    )

    def __init__(self, node: Node, data: LavalinkStatsOpObject):
        self._node = node
        self._data = data
        self._memory = data.memory
        self._cpu = data.cpu
        self._frame_stats = data.frameStats
        self._penalty = Penalty(self)

    @property
    def uptime(self) -> int:
        """How long the node has been running for in milliseconds"""
        return self._data.uptime

    @property
    def uptime_seconds(self) -> float:
        """How long the node has been running for in seconds"""
        return self.uptime / 1000

    @property
    def players(self) -> int:
        """The amount of players connected to the node"""
        return self._data.players or self._node.connected_count

    @property
    def playing_players(self) -> int:
        """The amount of players that are playing in the node"""
        return self._data.playingPlayers or self._node.playing_count

    @property
    def memory_free(self) -> int:
        """The amount of memory free to the node"""
        return self._memory.free

    @property
    def memory_used(self) -> int:
        """The amount of memory that is used by the node"""
        return self._memory.used

    @property
    def memory_allocated(self) -> int:
        """The amount of memory allocated to the node"""
        return self._memory.allocated

    @property
    def memory_reservable(self) -> int:
        """The amount of memory reservable to the node"""
        return self._memory.reservable

    @property
    def cpu_cores(self) -> int:
        """The amount of cpu cores the system of the node has"""
        return self._cpu.cores

    @property
    def system_load(self) -> float:
        """The overall CPU load of the system"""
        return self._cpu.systemLoad

    @property
    def lavalink_load(self) -> float:
        """The CPU load generated by Lavalink"""
        return self._cpu.lavalinkLoad

    @property
    def frames_sent(self) -> int:
        """The number of frames sent to Discord.
        Warning
        -------
        Given that audio packets are sent via UDP, this number may not be 100% accurate due to dropped packets.
        """
        return self._frame_stats.sent if self._frame_stats else -1

    @property
    def frames_nulled(self) -> int:
        """The number of frames that yielded null, rather than actual data"""
        return self._frame_stats.nulled if self._frame_stats else -1

    @property
    def frames_deficit(self) -> int:
        """The number of missing frames. Lavalink generates this figure by calculating how many packets to expect
        per minute, and deducting ``frames_sent``. Deficit frames could mean the CPU is overloaded, and isn't
        generating frames as quickly as it should be.
        """
        return self._frame_stats.deficit if self._frame_stats else -1

    @property
    def penalty(self) -> Penalty:
        """The penalty for the node"""
        return self._penalty

    def __repr__(self):
        return (
            f"<Stats node_id={self._node.identifier} "
            f"uptime={self.uptime} "
            f"players={self.players} "
            f"playing_players={self.playing_players} "
            f"memory_free={self.memory_free} "
            f"memory_used={self.memory_used} "
            f"memory_allocated={self.memory_allocated} "
            f"memory_reservable={self.memory_reservable} "
            f"cpu_cores={self.cpu_cores} "
            f"system_load={self.system_load} "
            f"lavalink_load={self.lavalink_load} "
            f"frames_sent={self.frames_sent} "
            f"frames_nulled={self.frames_nulled} "
            f"frames_deficit={self.frames_deficit}> "
            f"penalty={self.penalty}>"
        )


class Node:
    """Represents a Node connection with Lavalink.

    Note
    ----
    Nodes are **NOT** meant to be added manually, but rather with :func:`Client.add_node`.

    Attributes
    ----------
    host: :class:`str`
        The address of the Lavalink node.
    port: Optional[:class:`int`]
        The port to use for websocket and REST connections.
    password: :class:`str`
        The password used for authentication.
    name: :class:`str`
        The name the :class:`Node` is identified by.
    ssl: :class:`bool`
        Whether to use a ssl connection.
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
        "_resume_key",
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
        "trace",
        "_logger",
    )

    def __init__(
        self,
        manager: NodeManager,
        host: str,
        password: str,
        resume_key: str,
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
    ):
        from pylav.query import Query

        self._query_cls: Query = Query  # type: ignore
        self._version: Version | LegacyVersion | None = None
        self._api_version: int | None = None
        self._manager = manager
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), json_serialize=ujson.dumps)
        self._temporary = temporary
        if not temporary:
            self._config: NodeModel = self._manager._client.node_db_manager.get_node_config(unique_identifier)
        else:
            self._config: NodeModelMock = None
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

        self._resume_key = resume_key or self._identifier
        self._resume_timeout = resume_timeout
        self._reconnect_attempts = reconnect_attempts
        self._search_only = search_only
        self._capabilities: set[str] = set()
        self._coordinates = (0, 0)
        self._down_votes = ExpiringDict(max_len=float("inf"), max_age_seconds=600)  # type: ignore
        cli_flags = getattr("manager._client.bot", "_cli_flags", None)
        self.trace = cli_flags.logging_level < logging.INFO if cli_flags else False

        self._stats = None
        from pylav.websocket import WebSocket

        self._ready = asyncio.Event()
        self._ws = WebSocket(
            node=self,
            host=self.host,
            port=self.port,
            password=self.password,
            resume_key=self.resume_key,
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
            next_run_time=utcnow() + datetime.timedelta(seconds=15),
        )

    async def _unhealthy(self):
        del self.down_votes
        if self._ws is not None:
            await self.websocket.manual_closure(
                managed_node=self.identifier == self.node_manager.client.bot.user.id and self.websocket is not None
            )
        if self.identifier == self.node_manager.client.bot.user.id:
            await self.node_manager.client.managed_node_controller.restart()
            with contextlib.suppress(Exception):
                await self.close()

    async def node_monitor_task(self):
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            try:
                await self.websocket.ping()
                await self.get_version(raise_on_error=True)
                self._logger.trace("Healthy")
            except Exception:
                if self.websocket._connecting is True:
                    self._logger.debug("Already connecting - skipping reconnect on unhealthy")
                    return
                self._logger.warning("Unhealthy - Triggering a state reset")
                await self._unhealthy()

            playing_players = len(self.playing_players)
            if playing_players == 0:
                return
            if (self.down_votes / playing_players) >= 0.5:
                if self.websocket._connecting is True:
                    self._logger.debug("Already connecting - skipping reconnect on unhealthy")
                    return
                await self._unhealthy()

    @property
    def version(self) -> Version | LegacyVersion | None:
        return self._version

    @property
    def api_version(self) -> int | None:
        return self._api_version

    @property
    def socket_protocol(self) -> str:
        """The protocol used for the socket connection"""
        return "wss" if self._ssl else "ws"

    @property
    def is_ready(self) -> bool:
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
        return self._managed

    @property
    def config(self) -> NodeModelMock | NodeModel:
        return self._config

    @property
    def identifier(self) -> int:
        """
        The identifier of the :class:`Node`.
        """
        return self._identifier

    @property
    def search_only(self) -> bool:
        return self._search_only

    @property
    def session(self) -> aiohttp.ClientSession:
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
    def resume_key(self) -> str:
        """The resume key of the node"""
        return self._resume_key

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
        return [p for p in self._manager.client.player_manager.players.values() if p._original_node == self]

    @property
    def players(self) -> list[Player]:
        """Returns a list of all players on this node"""
        return [p for p in self._manager.client.player_manager.players.values() if p.node == self]

    @property
    def playing_players(self) -> list[Player]:
        """Returns a list of all players on this node that are playing"""
        return [p for p in self.players if p.is_playing]

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
        if not player.is_playing:
            return -1
        self._down_votes[player.guild.id] = 1
        return self.down_votes

    def down_unvote(self, player: Player) -> int:
        """Removes a down vote for this node"""
        if not player.is_playing:
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

    async def penalty_with_region(self, region: str | None) -> float:
        """The penalty for the node, with the region added in"""
        if not region:
            return self.penalty
        return self.penalty + (1.1 ** (0.0025 * await self.region_distance(region)) * 500 - 500)

    def dispatch_event(self, event: Event) -> None:
        """|coro|
        Dispatches the given event to all registered hooks.
        Parameters
        ----------
        event: :class:`Event`
            The event to dispatch to the hooks.
        """
        self.node_manager.client.dispatch_event(event)

    def __repr__(self):
        return (
            f"<Node id={self.identifier} name={self.name} session_id={self.session_id} "
            f"region={self.region} ssl={self.ssl} "
            f"search_only={self.search_only} connected={self.websocket.connected if self._ws else False} "
            f"votes={self.down_votes} "
            f"players={self.server_connected_players} playing={self.server_playing_players}>"
        )

    def __eq__(self, other):
        if isinstance(other, Node):
            return functools.reduce(
                lambda x, y: x and y,
                map(
                    lambda p, q: p == q,
                    [self.identifier, self.websocket.connected, self.name, self._resume_key],
                    [other.identifier, self.websocket.connected, self.name, self._resume_key],
                ),
                True,
            )
        elif isinstance(other, NodeModel):
            return self.identifier == other.id
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Node):
            return self.identifier != other.identifier
        elif isinstance(other, NodeModel):
            return self.identifier != other.id
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.host, self.port))

    @staticmethod
    def parse_loadtrack_response(data: LoadTracksResponseT) -> LavalinkLoadTrackObjects:
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
            case "LOAD_FAILED":
                return from_dict(data_class=LavalinkLoadFailedObject, data=data)
            case "NO_MATCHES":
                return from_dict(data_class=LavalinkNoMatchesObject, data=data)
            case "PLAYLIST_LOADED":
                return from_dict(data_class=LavalinkPlaylistLoadedObject, data=data)
            case "TRACK_LOADED":
                return from_dict(data_class=LavalinkTrackLoadedObject, data=data)
            case "SEARCH_RESULT":
                return from_dict(data_class=LavalinkSearchResultObject, data=data)

    async def get_unsupported_features(self) -> set[str]:
        await self.update_features()
        return SUPPORTED_SOURCES.union(SUPPORTED_FEATURES) - self._capabilities

    async def update_features(self) -> set[str]:
        """|coro|
        Updates the features of the target node.
        """
        info = await self.get_info()
        for source in info.sourceManagers:
            self._capabilities.add(source)
        if not self.managed:
            self._capabilities.discard("local")
        if self.identifier in PYLAV_NODES:
            self._capabilities.discard("http")
            self._capabilities.discard("local")
        for plugin in info.plugins:
            match plugin.name:
                case "SponsorBlock-Plugin":
                    self._capabilities.add("sponsorblock")
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

    async def update_disabled_sources(self, sources: set[str]) -> None:
        """
        Updates the disabled sources.

        Returns
        -------
        :class:`None`
        """
        if self.managed or self.identifier in BUNDLED_NODES_IDS_HOST_MAPPING:
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
    ) -> LavalinkTrackLoadedObject | LavalinkPlaylistLoadedObject | LavalinkSearchResultObject:
        if response := await self.node_manager.client.query_cache_manager.fetch_query(query):
            load_type = (
                "PLAYLIST_LOADED"
                if query.is_playlist or query.is_album
                else "SEARCH_RESULT"
                if query.is_search
                else "TRACK_LOADED"
            )
            tracks = await response.fetch_tracks()
            tracks = (
                [decode_track(track)[0].to_dict() async for track in AsyncIter([tracks[0]] if first else tracks)]
                if tracks
                else []
            )
            data = {
                "loadType": load_type,
                "tracks": tracks,
                "playlistInfo": {"selectedTrack": -1, "name": await response.fetch_name()},
            }
            return self.parse_loadtrack_response(data)

    # ENDPOINTS
    def get_endpoint_websocket(self) -> str:
        match self.api_version:
            case 3:
                return f"{self.socket_protocol}://{self.host}:{self.port}/v3/websocket"
            case 4:
                return f"{self.socket_protocol}://{self.host}:{self.port}/v4/websocket"
        raise UnsupportedNodeAPI()

    def get_endpoint_info(self) -> str:
        match self.api_version:
            case 3:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v3/info"
            case 4:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v4/info"
        raise UnsupportedNodeAPI()

    def get_endpoint_session_players(self) -> str:
        match self.api_version:
            case 3:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v3/sessions/{self.session_id}/players"
            case 4:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v4/sessions/{self.session_id}/players"
        raise UnsupportedNodeAPI()

    def get_endpoint_session_player_by_guild_id(self, guild_id: int) -> str:
        match self.api_version:
            case 3:
                return (
                    f"{self.connection_protocol}://{self.host}:{self.port}/v3"
                    f"/sessions/{self.session_id}/players/{guild_id}"
                )
            case 4:
                return (
                    f"{self.connection_protocol}://{self.host}:{self.port}/v4"
                    f"/sessions/{self.session_id}/players/{guild_id}"
                )
        raise UnsupportedNodeAPI()

    def get_endpoint_session(self) -> str:
        match self.api_version:
            case 3:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v3/sessions/{self.session_id}"
            case 4:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v4/sessions/{self.session_id}"
        raise UnsupportedNodeAPI()

    def get_endpoint_loadtracks(self) -> str:
        match self.api_version:
            case 3:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v3/loadtracks"
            case 4:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v4/loadtracks"
        raise UnsupportedNodeAPI()

    def get_endpoint_decodetrack(self) -> str:
        match self.api_version:
            case 3:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v3/decodetrack"
            case 4:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v4/decodetrack"
        raise UnsupportedNodeAPI()

    def get_endpoint_decodetracks(self) -> str:
        match self.api_version:
            case 3:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v3/decodetracks"
            case 4:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v4/decodetracks"
        raise UnsupportedNodeAPI()

    def get_endpoint_stats(self) -> str:
        match self.api_version:
            case 3:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v3/stats"
            case 4:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v4/stats"
        raise UnsupportedNodeAPI()

    def get_endpoint_routeplanner_status(self) -> str:
        match self.api_version:
            case 3:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v3/routeplanner/status"
            case 4:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v4/routeplanner/status"
        raise UnsupportedNodeAPI()

    def get_endpoint_routeplanner_free_address(self) -> str:
        match self.api_version:
            case 3:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v3/routeplanner/free/address"
            case 4:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v4/routeplanner/free/address"
        raise UnsupportedNodeAPI()

    def get_endpoint_routeplanner_free_all(self) -> str:
        match self.api_version:
            case 3:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v3/routeplanner/free/all"
            case 4:
                return f"{self.connection_protocol}://{self.host}:{self.port}/v4/routeplanner/free/all"
        raise UnsupportedNodeAPI()

    def get_endpoint_version(self) -> str:
        return f"{self.connection_protocol}://{self.host}:{self.port}/version"

    # REST API - Direct calls
    async def get_session_players(self) -> list[LavalinkPlayerObject] | HTTPError:
        """|coro|
        Gets all players associated with the target node.

        Returns
        -------
        list[LavalinkPlayerObject]
            A list of all players associated with the target node.
        """
        async with self._session.get(
            self.get_endpoint_session_players(),
            headers={"Authorization": self.password},
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return [from_dict(data_class=LavalinkPlayerObject, data=t) for t in await res.json(loads=ujson.loads)]
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                raise Unauthorized(failure)
            self._logger.trace("Failed to get session players: %d %s", failure.status, failure.message)
            return HTTPError(failure)

    async def get_session_player(self, guild_id: int) -> LavalinkPlayerObject | HTTPError:
        async with self._session.get(
            self.get_endpoint_session_player_by_guild_id(guild_id=guild_id),
            headers={"Authorization": self.password},
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=LavalinkPlayerObject, data=await res.json(loads=ujson.loads))
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                raise Unauthorized(failure)
            self._logger.trace("Failed to get session player: %d %s", failure.status, failure.message)
            return HTTPError(failure)

    async def patch_session_player(
        self, guild_id: int, no_replace: bool = False, payload: RestPatchPlayerPayloadT = None
    ) -> LavalinkPlayerObject | HTTPError:
        async with self._session.patch(
            self.get_endpoint_session_player_by_guild_id(guild_id=guild_id),
            headers={"Authorization": self.password},
            params={"noReplace": "true" if no_replace else "false", "trace": "true" if self.trace else "false"},
            json=payload,
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=LavalinkPlayerObject, data=await res.json(loads=ujson.loads))
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                raise Unauthorized(failure)
            self._logger.trace("Failed to patch session player: %d %s", failure.status, failure.message)
            return HTTPError(failure)

    async def delete_session_player(self, guild_id: int) -> None | HTTPError:
        async with self._session.delete(
            self.get_endpoint_session_player_by_guild_id(guild_id=guild_id),
            headers={"Authorization": self.password},
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE or res.status in [404]:
                return
            response = await res.json(loads=ujson.loads)
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=response)
            if res.status in [401, 403]:
                raise Unauthorized(failure)
            self._logger.trace("Failed to delete session player: %d %s", failure.status, failure.message)
            return HTTPError(failure)

    async def patch_session(self, payload: RestPatchSessionPayloadT) -> None | HTTPError:
        async with self._session.patch(
            self.get_endpoint_session(),
            headers={"Authorization": self.password},
            json=payload,
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                raise Unauthorized(failure)
            self._logger.trace("Failed to delete session player: %d %s", failure.status, failure.message)
            return HTTPError(failure)

    async def get_loadtracks(self, query: Query) -> LavalinkLoadTrackObjects | HTTPError:
        if not self.available or not self.has_source(query.requires_capability):
            return dataclasses.replace(NO_MATCHES)

        async with self._session.get(
            self.get_endpoint_loadtracks(),
            headers={"Authorization": self.password},
            params={"identifier": query.query_identifier, "trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                result = await res.json(loads=ujson.loads)
                asyncio.create_task(self.node_manager.client.query_cache_manager.add_query(query, result))
                return self.parse_loadtrack_response(result)
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                raise Unauthorized(failure)
            self._logger.trace("Failed to load track: %d %s", failure.status, failure.message)
            return HTTPError(failure)

    async def get_decodetrack(
        self, encoded_track: str, timeout: aiohttp.ClientTimeout | object = sentinel
    ) -> LavalinkTrackObject | HTTPError:
        async with self._session.get(
            self.get_endpoint_decodetrack(),
            headers={"Authorization": self.password},
            params={"encodedTrack": encoded_track, "trace": "true" if self.trace else "false"},
            timeout=timeout,
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=LavalinkTrackObject, data=await res.json(loads=ujson.loads))
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                raise Unauthorized(failure)
            self._logger.trace("Failed to decode track: %d %s", failure.status, failure.message)
            return HTTPError(failure)

    async def post_decodetracks(self, encoded_tracks: list[str]) -> list[LavalinkTrackObject] | HTTPError:
        async with self._session.post(
            self.get_endpoint_decodetracks(),
            headers={"Authorization": self.password},
            json=encoded_tracks,
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return [from_dict(data_class=LavalinkTrackObject, data=t) for t in await res.json(loads=ujson.loads)]
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                raise Unauthorized(failure)
            self._logger.trace("Failed to decode tracks: %d %s", failure.status, failure.message)
            return HTTPError(failure)

    async def get_info(self, raise_on_error: bool = False) -> LavalinkInfoObject | HTTPError:
        async with self._session.get(
            self.get_endpoint_info(),
            headers={"Authorization": self.password},
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=LavalinkInfoObject, data=await res.json(loads=ujson.loads))
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                if raise_on_error:
                    raise Unauthorized(failure)
                return Unauthorized(failure)
            self._logger.trace("Failed to get info: %d %s", failure.status, failure.message)
            if raise_on_error:
                raise HTTPError(failure)
            return HTTPError(failure)

    async def get_stats(self, raise_on_error: bool = False) -> LavalinkStatsOpObject | HTTPError:
        async with self._session.get(
            self.get_endpoint_stats(),
            headers={"Authorization": self.password},
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=LavalinkStatsOpObject, data=await res.json(loads=ujson.loads))
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                if raise_on_error:
                    raise Unauthorized(failure)
                return HTTPError(failure)
            self._logger.trace("Failed to get stats: %d %s", failure.status, failure.message)
            if raise_on_error:
                raise HTTPError(failure)
            return HTTPError(failure)

    async def get_version(self, raise_on_error: bool = False) -> Version | LegacyVersion | HTTPError:
        async with self._session.get(
            self.get_endpoint_version(),
            headers={"Authorization": self.password, "Content-Type": "text/plain"},
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                text = await res.text()
                # TODO:  Have a better implementation for this
                if match := SNAPSHOT_REGEX.match(text):
                    return Version(f"3.999.0-alpha+{match.group('commit')}")
                return parse_version(await res.text())
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                if raise_on_error:
                    raise Unauthorized(failure)
                return HTTPError(failure)
            self._logger.trace("Failed to get version: %d %s", failure.status, failure.message)
            if raise_on_error:
                raise HTTPError(failure)
            return HTTPError(failure)

    async def get_routeplanner_status(self) -> RoutePlannerStatusResponseObject | HTTPError:
        async with self._session.get(
            self.get_endpoint_routeplanner_status(),
            headers={"Authorization": self.password},
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                data = await res.json(loads=ujson.loads)
                data["type"] = data["class"]
                del data["class"]
                return from_dict(data_class=RoutePlannerStatusResponseObject, data=data)
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                raise Unauthorized(failure)
            self._logger.trace("Failed to get routeplanner status: %d %s", failure.status, failure.message)
            return HTTPError(failure)

    async def post_routeplanner_free_address(self, address: str) -> None | HTTPError:
        async with self._session.post(
            self.get_endpoint_routeplanner_free_address(),
            headers={"Authorization": self.password},
            json={"address": address},
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                raise Unauthorized(failure)
            self._logger.trace("Failed to free routeplanner address: %d %s", failure.status, failure.message)
            return HTTPError(failure)

    async def post_routeplanner_free_all(self) -> None | HTTPError:
        async with self._session.post(
            self.get_endpoint_routeplanner_free_all(),
            headers={"Authorization": self.password},
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return
            failure = from_dict(data_class=LavalinkErrorResponseObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                raise Unauthorized(failure)
            self._logger.trace("Failed to free all routeplanner addresses: %d %s", failure.status, failure.message)
            return HTTPError(failure)

    # REST API - Wrappers

    async def fetch_node_version(self) -> Version | LegacyVersion:
        self._version = await self.get_version()
        return self._version

    async def fetch_api_version(self):
        if self.version is None:
            await self.fetch_node_version()
        if self.version < (v370 := Version("3.7.0-alpha")):
            self._api_version = None
        elif v370 <= self.version < (v400 := Version("4.0.0-alpha")):
            self._api_version = 3
        elif v400 <= self.version < Version("5.0.0-alpha"):
            self._api_version = 4
        else:
            raise UnsupportedNodeAPI()

    async def get_guild_player(self, guild_id: int) -> LavalinkPlayerObject:
        async with self._session.get(
            self.get_endpoint_session_player_by_guild_id(guild_id=guild_id),
            headers={"Authorization": self.password},
            params={"trace": "true" if self.trace else "false"},
        ) as res:
            if res.status in GOOD_RESPONSE_RANGE:
                return from_dict(data_class=LavalinkPlayerObject, data=await res.json(loads=ujson.loads))
            if res.status in [401, 403]:
                raise Unauthorized
        raise ValueError(f"Server returned an unexpected return code: {res.status}")

    async def get_track(
        self, query: Query, first: bool = False, bypass_cache: bool = False
    ) -> LavalinkLoadTrackObjects:
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
        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response object
        """
        if not bypass_cache:
            if cached_entry := await self.get_track_from_cache(query=query, first=first):
                return cached_entry
        response = await self.get_loadtracks(query=query)
        if first:
            return dataclasses.replace(response, tracks=response.tracks[:1])
        return response

    async def search_youtube_music(self, query: str, bypass_cache: bool = False) -> LavalinkLoadTrackObjects:
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

    async def search_youtube(self, query: str, bypass_cache: bool = False) -> LavalinkLoadTrackObjects:
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

    async def search_soundcloud(self, query: str, bypass_cache: bool = False) -> LavalinkLoadTrackObjects:
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

    async def search_spotify(self, query: str, bypass_cache: bool = False) -> LavalinkLoadTrackObjects:
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

    async def search_apple_music(self, query: str, bypass_cache: bool = False) -> LavalinkLoadTrackObjects:
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

    async def search_deezer(self, query: str, bypass_cache: bool = False) -> LavalinkLoadTrackObjects:
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

    async def search_yandex(self, query: str, bypass_cache: bool = False) -> LavalinkLoadTrackObjects:
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

    async def get_query_speak(self, query: str, bypass_cache: bool = False) -> LavalinkLoadTrackObjects:
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
        self, query: str, bypass_cache: bool = True, first: bool = True
    ) -> LavalinkLoadTrackObjects:
        """|coro|
        Gets the query from Localfiles.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        bypass_cache: :class:`bool`
            Whether to bypass the cache.
        first: :class:`bool`
            Whether to return the first result only.

        Returns
        -------
        LavalinkLoadTrackObjects
            Lavalink LoadTrack Response Object
        """
        response = await self.get_track(await self._query_cls.from_string(query), bypass_cache=bypass_cache)
        return (response.tracks[0] if response.tracks else None) if first else response

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
        echo: Echo = None,
        reset_no_set: bool = False,
        reset: bool = False,
    ) -> FiltersT | None:
        if reset:
            return None

        payload: FiltersT = {}
        self._get_filter_payload_volume(payload, volume)
        self._get_filter_payload_equalizer(equalizer, payload, player, reset_no_set)
        self._get_filter_payload_karaoke(karaoke, payload, player, reset_no_set)
        self._get_filter_payload_timescale(payload, player, reset_no_set, timescale)
        self._get_filter_payload_tremolo(payload, player, reset_no_set, tremolo)
        self._get_filter_payload_vibrato(payload, player, reset_no_set, vibrato)
        self._get_filter_payload_rotation(payload, player, reset_no_set, rotation)
        self._get_filter_payload_distortion(distortion, payload, player, reset_no_set)
        self._get_filter_payload_low_pass(low_pass, payload, player, reset_no_set)
        self._get_filter_payload_channel_mix(channel_mix, payload, player, reset_no_set)
        self._get_filter_payload_echo(echo, payload, player, reset_no_set)

        return payload

    @staticmethod
    def _get_filter_payload_volume(payload, volume):
        if volume:
            payload["volume"] = volume.get()

    @staticmethod
    def _get_filter_payload_echo(echo, payload, player, reset_no_set):
        if echo:
            payload["echo"] = echo.get()
        elif not reset_no_set and player.echo.changed:
            payload["echo"] = player.echo.get()

    @staticmethod
    def _get_filter_payload_channel_mix(channel_mix, payload, player, reset_no_set):
        if channel_mix:
            payload["channelMix"] = channel_mix.get()
        elif not reset_no_set and player.channel_mix.changed:
            payload["channelMix"] = player.channel_mix.get()

    @staticmethod
    def _get_filter_payload_low_pass(low_pass, payload, player, reset_no_set):
        if low_pass:
            payload["lowPass"] = low_pass.get()
        elif not reset_no_set and player.low_pass.changed:
            payload["lowPass"] = player.low_pass.get()

    @staticmethod
    def _get_filter_payload_distortion(distortion, payload, player, reset_no_set):
        if distortion:
            payload["distortion"] = distortion.get()
        elif not reset_no_set and player.distortion.changed:
            payload["distortion"] = player.distortion.get()

    @staticmethod
    def _get_filter_payload_rotation(payload, player, reset_no_set, rotation):
        if rotation:
            payload["rotation"] = rotation.get()
        elif not reset_no_set and player.rotation.changed:
            payload["rotation"] = player.rotation.get()

    @staticmethod
    def _get_filter_payload_vibrato(payload, player, reset_no_set, vibrato):
        if vibrato:
            payload["vibrato"] = vibrato.get()
        elif not reset_no_set and player.vibrato.changed:
            payload["vibrato"] = player.vibrato.get()

    @staticmethod
    def _get_filter_payload_tremolo(payload, player, reset_no_set, tremolo):
        if tremolo:
            payload["tremolo"] = tremolo.get()
        elif not reset_no_set and player.timescale.changed:
            payload["timescale"] = player.timescale.get()

    @staticmethod
    def _get_filter_payload_timescale(payload, player, reset_no_set, timescale):
        if timescale:
            payload["timescale"] = timescale.get()
        elif not reset_no_set and player.timescale.changed:
            payload["timescale"] = player.timescale.get()

    @staticmethod
    def _get_filter_payload_karaoke(karaoke, payload, player, reset_no_set):
        if karaoke:
            payload["karaoke"] = karaoke.get()
        elif not reset_no_set and player.karaoke.changed:
            payload["karaoke"] = player.karaoke.get()

    @staticmethod
    def _get_filter_payload_equalizer(equalizer, payload, player, reset_no_set):
        if equalizer:
            payload["equalizer"] = equalizer.get()
        elif not reset_no_set and player.equalizer.changed:
            payload["equalizer"] = player.equalizer.get()

    async def filters(
        self,
        *,
        guild_id: int,
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
    ):
        payload = self.get_filter_payload(
            player=self.node_manager.client.player_manager.get(guild_id),
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
            echo=echo,
        )
        await self.patch_session_player(
            guild_id=guild_id, payload=typing.cast(RestPatchPlayerPayloadT, {"filters": payload})
        )
