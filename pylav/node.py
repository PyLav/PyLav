from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import aiohttp
import ujson

from pylav.events import Event
from pylav.exceptions import Unauthorized
from pylav.filters import ChannelMix, Distortion, Equalizer, Karaoke, LowPass, Rotation, Timescale, Vibrato, Volume
from pylav.filters.tremolo import Tremolo
from pylav.utils import AsyncIter

if TYPE_CHECKING:
    from pylav.node_manager import NodeManager
    from pylav.player import Player
    from pylav.query import Query
    from pylav.websocket import WebSocket


class Penalty:
    """
    Represents the penalty of the stats of a Node.
    Attributes
    ----------
    player_penalty: :class:`int`
    cpu_penalty: :class:`int`
    null_frame_penalty: :class:`int`
    deficit_frame_penalty: :class:`int`
    total: :class:`int`
    """

    __slots__ = (
        "player_penalty",
        "cpu_penalty",
        "null_frame_penalty",
        "deficit_frame_penalty",
        "total",
    )

    def __init__(self, stats):
        self.player_penalty = stats.playing_players
        self.cpu_penalty = 1.05 ** (100 * stats.system_load) * 10 - 10
        self.null_frame_penalty = 0
        self.deficit_frame_penalty = 0

        if stats.frames_nulled != -1:
            self.null_frame_penalty = (1.03 ** (500 * (stats.frames_nulled / 3000))) * 300 - 300
            self.null_frame_penalty *= 2

        if stats.frames_deficit != -1:
            self.deficit_frame_penalty = (1.03 ** (500 * (stats.frames_deficit / 3000))) * 600 - 600

        self.total = self.player_penalty + self.cpu_penalty + self.null_frame_penalty + self.deficit_frame_penalty


class Stats:
    """
    Represents the stats of Lavalink node.
    Attributes
    ----------
    uptime: :class:`int`
        How long the node has been running for in milliseconds.
    players: :class:`int`
        The amount of players connected to the node.
    playing_players: :class:`int`
        The amount of players that are playing in the node.
    memory_free: :class:`int`
        The amount of memory free to the node.
    memory_used: :class:`int`
        The amount of memory that is used by the node.
    memory_allocated: :class:`int`
        The amount of memory allocated to the node.
    memory_reservable: :class:`int`
        The amount of memory reservable to the node.
    cpu_cores: :class:`int`
        The amount of cpu cores the system of the node has.
    system_load: :class:`int`
        The overall CPU load of the system.
    lavalink_load: :class:`int`
        The CPU load generated by Lavalink.
    frames_sent: :class:`int`
        The number of frames sent to Discord.
        Warning
        -------
        Given that audio packets are sent via UDP, this number may not be 100% accurate due to dropped packets.
    frames_nulled: :class:`int`
        The number of frames that yielded null, rather than actual data.
    frames_deficit: :class:`int`
        The number of missing frames. Lavalink generates this figure by calculating how many packets to expect
        per minute, and deducting ``frames_sent``. Deficit frames could mean the CPU is overloaded, and isn't
        generating frames as quickly as it should be.
    penalty: :class:`Penalty`
    """

    __slots__ = (
        "_node",
        "uptime",
        "players",
        "playing_players",
        "memory_free",
        "memory_used",
        "memory_allocated",
        "memory_reservable",
        "cpu_cores",
        "system_load",
        "lavalink_load",
        "frames_sent",
        "frames_nulled",
        "frames_deficit",
        "penalty",
    )

    def __init__(self, node, data):
        self._node = node

        self.uptime = data["uptime"]

        self.players = data["players"]
        self.playing_players = data["playingPlayers"]

        memory = data["memory"]
        self.memory_free = memory["free"]
        self.memory_used = memory["used"]
        self.memory_allocated = memory["allocated"]
        self.memory_reservable = memory["reservable"]

        cpu = data["cpu"]
        self.cpu_cores = cpu["cores"]
        self.system_load = cpu["systemLoad"]
        self.lavalink_load = cpu["lavalinkLoad"]

        frame_stats = data.get("frameStats", {})
        self.frames_sent = frame_stats.get("sent", -1)
        self.frames_nulled = frame_stats.get("nulled", -1)
        self.frames_deficit = frame_stats.get("deficit", -1)
        self.penalty = Penalty(self)


class Node:
    """
    Represents a Node connection with Lavalink.
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

    def __init__(
        self,
        manager: NodeManager,
        host: str,
        password: str,
        resume_key: str,
        resume_timeout: int,
        port: int | None = None,
        name: str | None = None,
        reconnect_attempts: int = 3,
        ssl: bool = False,
        search_only: bool = False,
        unique_identifier: str = None,
    ):
        from pylav.query import Query

        self._query_cls: Query = Query
        self._manager = manager
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), json_serialize=ujson.dumps)
        if unique_identifier is None:
            unique_identifier = str(uuid4())

        self._name = name or f"{self.region}-{self.host}-{unique_identifier}"
        if self._manager.get_node_by_id(unique_identifier) is not None:
            raise ValueError("A Node with identifier:%s already exists.")
        self._identifier = unique_identifier
        self._ssl = ssl
        if port is None:
            if self._ssl:
                self._port = 443
            else:
                self._port = 80
        else:
            self._port = port
        self._host = host
        self._password = password
        self._region = None

        self._resume_key = resume_key
        self._resume_timeout = resume_timeout
        self._reconnect_attempts = reconnect_attempts
        self._search_only = search_only
        self._capabilities = set()
        self._sources = set()

        self._stats = None
        from pylav.websocket import WebSocket

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

    @property
    def identifier(self) -> str:
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
        """The websocket of the node."""
        return self._ws

    @property
    def node_manager(self) -> NodeManager:
        """The :class:`NodeManager` this node belongs to."""
        return self._manager

    @property
    def port(self) -> int:
        """The port of the node."""
        return self._port

    @property
    def ssl(self) -> bool:
        """Whether the node is using a ssl connection."""
        return self._ssl

    @property
    def connection_protocol(self) -> str:
        """The protocol used for the connection."""
        return "https" if self.ssl else "http"

    @property
    def host(self) -> str:
        """The host of the node."""
        return self._host

    @property
    def region(self) -> str:
        """The region of the node."""
        return self._region

    @property
    def name(self) -> str:
        """The name of the node."""
        return self._name

    @property
    def password(self) -> str:
        """The password of the node."""
        return self._password

    @property
    def resume_key(self) -> str:
        """The resume key of the node."""
        return self._resume_key

    @property
    def resume_timeout(self) -> int:
        """The timeout to use for resuming."""
        return self._resume_timeout

    @property
    def reconnect_attempts(self) -> int:
        """The number of attempts to reconnect to the node."""
        return self._reconnect_attempts

    @property
    def stats(self) -> Stats:
        """The stats of the node."""
        return self._stats

    @stats.setter
    def stats(self, value: Stats) -> None:
        if not isinstance(value, Stats):
            raise TypeError("stats must be of type Stats")
        self._stats = value

    @property
    def available(self) -> bool:
        """Returns whether the node is available for requests."""
        return self._ws.connected

    @property
    def _original_players(self) -> list[Player]:
        """Returns a list of players that were assigned to this node, but were moved due to failover etc."""
        return [p for p in self._manager.client.player_manager.players.values() if p._original_node == self]  # noqa

    @property
    def players(self) -> list[Player]:
        """Returns a list of all players on this node."""
        return [p for p in self._manager.client.player_manager.players.values() if p.node == self]

    @property
    def playing_players(self) -> list[Player]:
        """Returns a list of all players on this node that are playing."""
        return [p for p in self.players if p.is_playing]

    @property
    def connected_players(self) -> list[Player]:
        """Returns a list of all players on this node that are connected."""
        return [p for p in self.players if p.is_connected]

    @property
    def count(self) -> int:
        """Returns the number of players on this node."""
        return len(self.players)

    @property
    def playing_count(self) -> int:
        """Returns the number of players on this node that are playing."""
        return len(self.playing_players)

    @property
    def connected_count(self) -> int:
        """Returns the number of players on this node that are connected."""
        return len(self.connected_players)

    @property
    def penalty(self) -> float:
        """Returns the load-balancing penalty for this node."""
        if not self.available or not self.stats:
            return 9e30

        return self.stats.penalty.total

    async def dispatch_event(self, event: Event) -> None:
        """|coro|
        Dispatches the given event to all registered hooks.
        Parameters
        ----------
        event: :class:`Event`
            The event to dispatch to the hooks.
        """
        await self.node_manager.client._dispatch_event(event)  # noqa

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
            f"region={self.region} ssl={self.ssl} search_only={self.search_only}>"
        )

    async def get_query_youtube_music(self, query: str) -> dict:
        """|coro|
        Gets the query from YouTube music.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        Returns
        -------
        list[dict]
            The list of results.
        """
        if not self.available:
            return []
        query = f"ytmsearch:{query}"
        return await self.get_tracks(await self._query_cls.from_string(query))

    async def get_query_youtube(self, query: str) -> dict:
        """|coro|
        Gets the query from YouTube music.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        Returns
        -------
        list[dict]
            The list of results.
        """
        if not self.available:
            return []
        query = f"ytsearch:{query}"
        return await self.get_tracks(await self._query_cls.from_string(query))

    async def get_query_soundcloud(self, query: str) -> dict:
        """|coro|
        Gets the query from Soundcloud.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        Returns
        -------
        list[dict]
            The list of results.
        """
        if not self.available:
            return []
        query = f"scsearch:{query}"
        return await self.get_tracks(await self._query_cls.from_string(query))

    async def get_query_tts(self, query: str) -> dict:
        """|coro|
        Gets the query for TTS.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        Returns
        -------
        list[dict]
            The list of results.
        """
        if not self.available:
            return []
        query = f"speak:{query}"
        return await self.get_tracks(await self._query_cls.from_string(query))

    async def get_query_spotify(self, query: str) -> dict:
        """|coro|
        Gets the query from Spotify.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        Returns
        -------
        list[dict]
            The list of results.
        """
        if not self.available:
            return []
        query = f"spsearch:{query}"
        return await self.get_tracks(await self._query_cls.from_string(query))

    async def get_query_apple_music(self, query: str) -> dict:
        """|coro|
        Gets the query from Apple Music.
        Parameters
        ----------
        query: :class:`str`
            The query to search for.
        Returns
        -------
        list[dict]
            The list of results.
        """
        if not self.available:
            return []
        query = f"amsearch:{query}"
        return await self.get_tracks(await self._query_cls.from_string(query))

    async def get_tracks(self, query: Query, first: bool = False) -> dict:
        """|coro|
        Gets all tracks associated with the given query.

        Parameters
        ----------
        query: :class:`Query`
            The query to perform a search for.
        first: :class:`bool`
            Whether to return the first result or all results.
        Returns
        -------
        :class:`dict`
            A dict representing tracks.
        """
        if response := await self.node_manager.client.query_cache_manager.get_query(query):
            # Note this is a partial return
            #   (the tracks are only B64 encoded, to get the decoded tracks like the api returns
            #   you'd need to call `pylava.utils.decode_tracks`)
            return {
                "playlistInfo:": {
                    "name": response.name,
                },
                "loadType':": "PlaylistLoaded"
                if query.is_playlist or query.is_album
                else "TrackLoaded"
                if not query.is_search
                else "SearchLoaded",
                "tracks": [{"track": track} async for track in AsyncIter(response.tracks)],
            }

        destination = f"{self.connection_protocol}://{self.host}:{self.port}/loadtracks"
        async with self._session.get(
            destination, headers={"Authorization": self.password}, params={"identifier": query.query_identifier}
        ) as res:
            if res.status == 200:
                result = await res.json(loads=ujson.loads)
                asyncio.create_task(self.node_manager.client.query_cache_manager.add_query(query, result))
                if first:
                    return next(iter(result.get("tracks", [])), {})
                return result
            if res.status == 401 or res.status == 403:
                raise Unauthorized
            return {}

    async def decode_track(self, track: str) -> dict | None:
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/decodetrack"
        async with self.session.get(
            destination, headers={"Authorization": self.password}, params={"track": track}
        ) as res:
            if res.status == 200:
                return await res.json(loads=ujson.loads)

            if res.status == 401 or res.status == 403:
                raise Unauthorized

            return None

    async def decode_tracks(self, tracks: list[str]) -> list[dict]:
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/decodetracks"
        async with self.session.get(destination, headers={"Authorization": self.password}, json=tracks) as res:
            if res.status == 200:
                return await res.json(loads=ujson.loads)

            if res.status == 401 or res.status == 403:
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

            if res.status == 401 or res.status == 403:
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
            if res.status == 401 or res.status == 403:
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
            if res.status == 401 or res.status == 403:
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

            if res.status == 401 or res.status == 403:
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

            if res.status == 401 or res.status == 403:
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
    ):
        op = {
            "op": "filters",
            "guildId": str(guild_id),
        }
        if volume and volume.changed:
            op["volume"] = volume.get()
        if equalizer and equalizer.changed:
            op["equalizer"] = equalizer.get()
        if karaoke and karaoke.changed:
            op["karaoke"] = karaoke.get()
        if timescale and timescale.changed:
            op["timescale"] = timescale.get()
        if tremolo and tremolo.changed:
            op["tremolo"] = tremolo.get()
        if vibrato and vibrato.changed:
            op["vibrato"] = vibrato.get()
        if rotation and rotation.changed:
            op["rotation"] = rotation.get()
        if distortion and distortion.changed:
            op["distortion"] = distortion.get()
        if low_pass and low_pass.changed:
            op["lowPass"] = low_pass.get()
        if channel_mix and channel_mix.changed:
            op["channelMix"] = channel_mix.get()

        await self.send(**op)

    async def update_features(self):
        """|coro|
        Updates the features of the target node.
        """
        for feature in await self.get_plugins():
            if feature["name"] == "Topis-Source-Managers-Plugin":
                self._capabilities.update(["spotify", "applemusic"])
            elif feature["name"] == "DuncteBot-plugin":
                self._capabilities.update(
                    ["getyarn", "clypit", "tts", "pornhub", "reddit", "ocremix", "tiktok", "mixcloud"]
                )
            elif feature["name"] == "Google Cloud TTS":
                self._capabilities.update(
                    "gctts",
                )
            elif feature["name"] == "sponsorblock":
                self._capabilities.add(
                    "sponsorblock",
                )
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

    def has_capability(self, capability: str) -> bool:
        """
        Checks if the target node has the specified capability.

        Parameters
        ----------
        capability: :class:`str`
            The capability to check.

        Returns
        -------
        :class:`bool`
            True if the target node has the specified capability, False otherwise.
        """
        return capability.lower() in self.capabilities

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
        return self.has_capability("spotify") and self.has_source("spotify")

    @property
    def supports_apple_music(self) -> bool:
        """
        Checks if the target node supports Apple Music.

        Returns
        -------
        :class:`bool`
            True if the target node supports Apple Music, False otherwise.
        """
        return self.has_capability("applemusic") and self.has_source("applemusic")

    @property
    def supports_getyarn(self) -> bool:
        """
        Checks if the target node supports GetYarn.

        Returns
        -------
        :class:`bool`
            True if the target node supports GetYarn, False otherwise.
        """
        return self.has_capability("getyarn") and self.has_source("getyarn")

    @property
    def supports_clypit(self) -> bool:
        """
        Checks if the target node supports ClypIt.

        Returns
        -------
        :class:`bool`
            True if the target node supports ClypIt, False otherwise.
        """
        return self.has_capability("clypit") and self.has_source("clypit")

    @property
    def supports_tts(self) -> bool:
        """
        Checks if the target node supports TTS.

        Returns
        -------
        :class:`bool`
            True if the target node supports TTS, False otherwise.
        """
        return self.has_capability("tts") and self.has_source("tts")

    @property
    def supports_gctts(self) -> bool:
        """
        Checks if the target node supports Google Cloud TTS.

        Returns
        -------
        :class:`bool`
            True if the target node supports Google Cloud TTS, False otherwise.
        """
        return self.has_capability("gctts")  # TODO: Check source name

    @property
    def supports_pornhub(self) -> bool:
        """
        Checks if the target node supports PornHub.

        Returns
        -------
        :class:`bool`
            True if the target node supports PornHub, False otherwise.
        """
        return self.has_capability("pornhub") and self.has_source("pornhub")

    @property
    def supports_reddit(self) -> bool:
        """
        Checks if the target node supports Reddit.

        Returns
        -------
        :class:`bool`
            True if the target node supports Reddit, False otherwise.
        """
        return self.has_capability("reddit") and self.has_source("reddit")

    @property
    def supports_ocremix(self) -> bool:
        """
        Checks if the target node supports OCRemix.

        Returns
        -------
        :class:`bool`
            True if the target node supports OCRemix, False otherwise.
        """
        return self.has_capability("ocremix") and self.has_source("ocremix")

    @property
    def supports_mixcloud(self) -> bool:
        """
        Checks if the target node supports Mixcloud.

        Returns
        -------
        :class:`bool`
            True if the target node supports Mixcloud, False otherwise.
        """
        return self.has_capability("mixcloud") and self.has_source("mixcloud")

    @property
    def supports_tiktok(self) -> bool:
        """
        Checks if the target node supports TikTok.

        Returns
        -------
        :class:`bool`
            True if the target node supports TikTok, False otherwise.
        """
        return self.has_capability("tiktok") and self.has_source("tiktok")

    @property
    def supports_youtube(self) -> bool:
        """
        Checks if the target node supports YouTube.

        Returns
        -------
        :class:`bool`
            True if the target node supports YouTube, False otherwise.
        """
        return self.has_source("youtube") and self.has_source("youtube")

    @property
    def supports_bandcamp(self) -> bool:
        """
        Checks if the target node supports Bandcamp.

        Returns
        -------
        :class:`bool`
            True if the target node supports Bandcamp, False otherwise.
        """
        return self.has_source("bandcamp") and self.has_source("bandcamp")

    @property
    def supports_soundcloud(self) -> bool:
        """
        Checks if the target node supports SoundCloud.

        Returns
        -------
        :class:`bool`
            True if the target node supports SoundCloud, False otherwise.
        """
        return self.has_source("soundcloud") and self.has_source("soundcloud")

    @property
    def supports_twitch(self) -> bool:
        """
        Checks if the target node supports Twitch.

        Returns
        -------
        :class:`bool`
            True if the target node supports Twitch, False otherwise.
        """
        return self.has_source("twitch") and self.has_source("twitch")

    @property
    def supports_vimeo(self) -> bool:
        """
        Checks if the target node supports Vimeo.

        Returns
        -------
        :class:`bool`
            True if the target node supports Vimeo, False otherwise.
        """
        return self.has_source("vimeo") and self.has_source("vimeo")

    @property
    def supports_http(self) -> bool:
        """
        Checks if the target node supports HTTP.

        Returns
        -------
        :class:`bool`
            True if the target node supports HTTP, False otherwise.
        """
        return self.has_source("http") and self.has_source("http")

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
        await self.session.close()
