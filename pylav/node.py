from __future__ import annotations

import asyncio
import contextlib
import datetime
import functools
import pathlib
import typing
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import aiohttp
import asyncstdlib
import ujson
from apscheduler.jobstores.base import JobLookupError
from discord.utils import utcnow
from expiringdict import ExpiringDict

from pylav._logging import getLogger
from pylav.constants import BUNDLED_NODES_IDS, PYLAV_NODES, REGION_TO_COUNTRY_COORDINATE_MAPPING, SUPPORTED_SOURCES
from pylav.events import Event
from pylav.exceptions import Unauthorized, WebsocketNotConnectedError
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
from pylav.types import LavalinkResponseT, TrackT
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
    _ = lambda x: x


LOGGER = getLogger("PyLav.Node")


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

    def __init__(self, node: Node, data: dict):
        self._node = node
        self._data = data
        self._memory = data["memory"]
        self._cpu = data["cpu"]
        self._frame_stats = data.get("frameStats", {})
        self._penalty = Penalty(self)

    @property
    def uptime(self) -> int:
        """How long the node has been running for in milliseconds"""
        return self._data["uptime"]

    @property
    def uptime_seconds(self) -> float:
        """How long the node has been running for in seconds"""
        return self.uptime / 1000

    @property
    def players(self) -> int:
        """The amount of players connected to the node"""
        return self._data["players"] or self._node.connected_count

    @property
    def playing_players(self) -> int:
        """The amount of players that are playing in the node"""
        return self._data["playingPlayers"] or self._node.playing_count

    @property
    def memory_free(self) -> int:
        """The amount of memory free to the node"""
        return self._memory["free"]

    @property
    def memory_used(self) -> int:
        """The amount of memory that is used by the node"""
        return self._memory["used"]

    @property
    def memory_allocated(self) -> int:
        """The amount of memory allocated to the node"""
        return self._memory["allocated"]

    @property
    def memory_reservable(self) -> int:
        """The amount of memory reservable to the node"""
        return self._memory["reservable"]

    @property
    def cpu_cores(self) -> int:
        """The amount of cpu cores the system of the node has"""
        return self._cpu["cores"]

    @property
    def system_load(self) -> float:
        """The overall CPU load of the system"""
        return self._cpu["systemLoad"]

    @property
    def lavalink_load(self) -> float:
        """The CPU load generated by Lavalink"""
        return self._cpu["lavalinkLoad"]

    @property
    def frames_sent(self) -> int:
        """The number of frames sent to Discord.
        Warning
        -------
        Given that audio packets are sent via UDP, this number may not be 100% accurate due to dropped packets.
        """
        return self._frame_stats.get("sent", -1)

    @property
    def frames_nulled(self) -> int:
        """The number of frames that yielded null, rather than actual data"""
        return self._frame_stats.get("nulled", -1)

    @property
    def frames_deficit(self) -> int:
        """The number of missing frames. Lavalink generates this figure by calculating how many packets to expect
        per minute, and deducting ``frames_sent``. Deficit frames could mean the CPU is overloaded, and isn't
        generating frames as quickly as it should be.
        """
        return self._frame_stats.get("deficit", -1)

    @property
    def penalty(self) -> Penalty:
        """The penalty for the node"""
        return self._penalty


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
        "_sources",
        "_capabilities",
        "_coordinates",
        "_down_votes",
        "_ready",
        "_ws",
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
        self._sources = self._capabilities = set()
        self._coordinates = (0, 0)
        self._down_votes = ExpiringDict(max_len=float("inf"), max_age_seconds=600)  # type: ignore

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
            seconds=5,
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
                LOGGER.trace("Node %s is healthy", self.name)
            except (WebsocketNotConnectedError, ConnectionResetError):
                LOGGER.warning("Node %s is unhealthy - Triggering a state reset", self.name)
                await self._unhealthy()

            playing_players = len(self.playing_players)
            if playing_players == 0:
                return
            if (self.down_votes / playing_players) >= 0.5:
                await self._unhealthy()

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

    async def send(self, **data: Any) -> None:
        """|coro|
        Sends the passed data to the node via the websocket connection.
        Parameters
        ----------
        data: class:`any`
            The dict to send to Lavalink.
        """
        await self.websocket.send(**data)

    def __repr__(self):
        return (
            f"<Node id={self.identifier} name={self.name} "
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

    async def get_query_youtube_music(self, query: str, bypass_cache: bool = False) -> LavalinkResponseT:
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
        list[dict]
            The list of results.
        """
        if not self.available:
            return {
                "loadType": "LOAD_FAILED",
                "playlistInfo": {"name": "", "selectedTrack": -1},
                "tracks": [],
            }
        query = f"ytmsearch:{query}"
        return await self.get_tracks(await self._query_cls.from_string(query), bypass_cache=bypass_cache)

    async def get_query_youtube(self, query: str, bypass_cache: bool = False) -> LavalinkResponseT:
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
        list[dict]
            The list of results.
        """
        if not self.available:
            return {
                "loadType": "LOAD_FAILED",
                "playlistInfo": {"name": "", "selectedTrack": -1},
                "tracks": [],
            }
        query = f"ytsearch:{query}"
        return await self.get_tracks(await self._query_cls.from_string(query), bypass_cache=bypass_cache)

    async def get_query_soundcloud(self, query: str, bypass_cache: bool = False) -> LavalinkResponseT:
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
        list[dict]
            The list of results.
        """
        if not self.available:
            return {
                "loadType": "LOAD_FAILED",
                "playlistInfo": {"name": "", "selectedTrack": -1},
                "tracks": [],
            }
        query = f"scsearch:{query}"
        return await self.get_tracks(await self._query_cls.from_string(query), bypass_cache=bypass_cache)

    async def get_query_speak(self, query: str, bypass_cache: bool = False) -> list | None:
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
        list[dict]
            The list of results.
        """
        if not self.available:
            return []
        if len(query) > 200:
            query = query[:200]
        query = f"speak:{query}"
        response = await self.get_tracks(
            await self._query_cls.from_string(query), bypass_cache=bypass_cache, first=True
        )
        return response.get("tracks")

    async def get_query_spotify(self, query: str, bypass_cache: bool = False) -> LavalinkResponseT:
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
        list[dict]
            The list of results.
        """
        if not self.available:
            return {
                "loadType": "LOAD_FAILED",
                "playlistInfo": {"name": "", "selectedTrack": -1},
                "tracks": [],
            }
        query = f"spsearch:{query}"
        return await self.get_tracks(await self._query_cls.from_string(query), bypass_cache=bypass_cache)

    async def get_query_apple_music(self, query: str, bypass_cache: bool = False) -> LavalinkResponseT:
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
        list[dict]
            The list of results.
        """
        if not self.available:
            return {
                "loadType": "LOAD_FAILED",
                "playlistInfo": {"name": "", "selectedTrack": -1},
                "tracks": [],
            }
        query = f"amsearch:{query}"
        return await self.get_tracks(await self._query_cls.from_string(query), bypass_cache=bypass_cache)

    async def get_query_localfiles(
        self, query: str, bypass_cache: bool = True, first: bool = True
    ) -> LavalinkResponseT | TrackT:
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
        list[dict]
            The list of results.
        """
        return (
            await self.get_tracks(
                await self._query_cls.from_string(query),
                bypass_cache=bypass_cache,
                first=first,
            )
            if self.available
            else {
                "loadType": "LOAD_FAILED",
                "playlistInfo": {"name": "", "selectedTrack": -1},
                "tracks": [],
            }
        )

    async def get_tracks(
        self, query: Query, first: bool = False, bypass_cache: bool = False
    ) -> LavalinkResponseT | TrackT:
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
        :class:`dict`
            A dict representing tracks.
        """
        if not bypass_cache and (response := await self.node_manager.client.query_cache_manager.fetch_query(query)):
            return typing.cast(
                LavalinkResponseT,
                {"track": await response.fetch_first()}
                if first
                else {
                    "playlistInfo": {
                        "name": await response.fetch_name(),
                    },
                    "loadType": "PLAYLIST_LOADED"
                    if query.is_playlist or query.is_album
                    else "SEARCH_RESULT"
                    if query.is_search
                    else "TRACK_LOADED",
                    "tracks": [{"track": track} async for track in AsyncIter(await response.fetch_tracks())],
                },
            )

        destination = f"{self.connection_protocol}://{self.host}:{self.port}/loadtracks"
        async with self._session.get(
            destination, headers={"Authorization": self.password}, params={"identifier": query.query_identifier}
        ) as res:
            if res.status == 200:
                result = await res.json(loads=ujson.loads)
                asyncio.create_task(self.node_manager.client.query_cache_manager.add_query(query, result))
                if first:
                    return await asyncstdlib.anext(  # type:ignore
                        asyncstdlib.iter(result.get("tracks", [])), default={}
                    )
                return result
            if res.status in [401, 403]:
                raise Unauthorized
            return {}

    async def decode_track(self, track: str) -> TrackT | None:
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/decodetrack"
        async with self.session.get(
            destination, headers={"Authorization": self.password}, params={"track": track}
        ) as res:
            if res.status == 200:
                return await res.json(loads=ujson.loads)

            if res.status in [401, 403]:
                raise Unauthorized

            return None

    async def decode_tracks(self, tracks: list[str]) -> list[TrackT]:
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/decodetracks"
        async with self.session.get(destination, headers={"Authorization": self.password}, json=tracks) as res:
            if res.status == 200:
                return await res.json(loads=ujson.loads)

            if res.status in [401, 403]:
                raise Unauthorized
            return []

    async def routeplanner_status(self) -> dict | None:
        """|coro|
        Gets the route-planner status of the target node.

        Returns
        -------
        :class:`dict`
            A dict representing the route-planner information.
        """
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/routeplanner/status"
        async with self._session.get(destination, headers={"Authorization": self.password}) as res:
            if res.status == 200:
                return await res.json(loads=ujson.loads)

            if res.status in [401, 403]:
                raise Unauthorized
            return None

    async def routeplanner_free_address(self, address: str) -> bool:
        """|coro|
        Gets the route-planner status of the target node.

        Parameters
        ----------
        address: :class:`str`
            The address to free.

        Returns
        -------
        :class:`bool`
            True if the address was freed, False otherwise.
        """
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/routeplanner/free/address"

        async with self._session.post(
            destination, headers={"Authorization": self.password}, json={"address": address}
        ) as res:
            if res.status in [401, 403]:
                raise Unauthorized
            return res.status == 204

    async def routeplanner_free_all_failing(self) -> bool:
        """|coro|
        Gets the route-planner status of the target node.

        Returns
        -------
        :class:`bool`
            True if all failing addresses were freed, False otherwise.
        """
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/routeplanner/free/all"

        async with self._session.post(destination, headers={"Authorization": self.password}) as res:
            if res.status in [401, 403]:
                raise Unauthorized
            return res.status == 204

    async def get_plugins(self) -> list[dict]:
        """|coro|
        Gets the plugins of the target node.

        Returns
        -------
        :class:`list` of :class:`dict`
            A dict representing the plugins.
        """
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/plugins"
        async with self._session.get(destination, headers={"Authorization": self.password}) as res:
            if res.status == 200:
                return await res.json(loads=ujson.loads)

            if res.status in [401, 403]:
                raise Unauthorized
        return []

    async def get_sources(self) -> dict:
        """|coro|
        Gets the sources of the target node.

        Returns
        -------
        :class:`dict`
            A dict representing the sources.
        """
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/sources"
        async with self._session.get(destination, headers={"Authorization": self.password}) as res:
            if res.status == 200:
                return await res.json(loads=ujson.loads)

            if res.status in [401, 403]:
                raise Unauthorized
        return {}

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
        op = {
            "op": "filters",
            "guildId": str(guild_id),
        }
        if volume:
            op["volume"] = volume.get()
        if equalizer:
            op["equalizer"] = equalizer.get()
        if karaoke:
            op["karaoke"] = karaoke.get()
        if timescale:
            op["timescale"] = timescale.get()
        if tremolo:
            op["tremolo"] = tremolo.get()
        if vibrato:
            op["vibrato"] = vibrato.get()
        if rotation:
            op["rotation"] = rotation.get()
        if distortion:
            op["distortion"] = distortion.get()
        if low_pass:
            op["lowPass"] = low_pass.get()
        if channel_mix:
            op["channelMix"] = channel_mix.get()
        if echo:
            op["echo"] = echo.get()

        await self.send(**op)

    async def get_unsupported_features(self) -> set[str]:
        await self.update_features()
        return SUPPORTED_SOURCES - self._capabilities

    async def update_features(self):
        """|coro|
        Updates the features of the target node.
        """
        # This is pending a pr being merged until it is it will not provide any useful info
        #    However once it is merged this should be the only method to get capabilities
        #    from the node.
        for source_origin, source_data in (await self.get_sources()).items():
            if source_origin == "defaults":
                for source_name, source_state in source_data.items():
                    if source_state:
                        self._sources.add(source_name)
            elif source_origin == "plugins":
                for _, plugin_data in source_data.items():
                    for source_name, source_state in plugin_data.items():
                        if source_state:
                            self._sources.add(source_name)
        if not self._sources:
            if self.managed:
                self._capabilities.add("local")
            # FIXME: Remove me when the PR upstream is merged
            # This only exists as the above does not provide any useful info currently.
            #    However once it is merged this should be removed as it is not a good way to assess capabilities.
            #    As even though a plugin may be enable the source it adds may be disabled.

            #   Since this assumes everything is enable is is bound to cause track exceptions to be thrown when
            #   a source required but assumed enabled is in actuality disabled.
            for feature in await self.get_plugins():
                if feature["name"] == "Topis-Source-Managers-Plugin":
                    self._capabilities.update(["spotify", "applemusic"])
                elif feature["name"] == "DuncteBot-plugin":
                    self._capabilities.update(
                        [
                            "getyarn",
                            "clypit",
                            "speak",
                            "pornhub",
                            "reddit",
                            "ocremix",
                            "tiktok",
                            "mixcloud",
                            "soundgasm",
                        ]
                    )
                elif feature["name"] == "Google Cloud TTS":
                    self._capabilities.update(
                        "gcloud-tts",
                    )
                elif feature["name"] == "sponsorblock":
                    self._capabilities.add(
                        "sponsorblock",
                    )
            self._capabilities.update(["youtube", "soundcloud", "twitch", "bandcamp", "vimeo", "http"])
        # Give that remove files will not play nice with local files lets disable it for all but the managed node
        #    While this locks out some remove nodes with the correct setup it ensures that we are consistently
        #    using the correct node which will support local files instead of trying and failing most of the time.
        if not self.managed:
            self._capabilities.discard("local")
        if self.identifier in PYLAV_NODES:
            self._capabilities.discard("http")
            self._capabilities.discard("local")
        # If not setup says these should be disabled remove them to trick the node to think they are disabled
        if self._sources:
            self._sources.difference_update(self._disabled_sources)

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
        if self.managed or self.identifier in BUNDLED_NODES_IDS:
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
        return self._sources.copy()

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
        return self.has_source("getyarn")

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
        return self.has_source("local") and self.has_source("local")

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
