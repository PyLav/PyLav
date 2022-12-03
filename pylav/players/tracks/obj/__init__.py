from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import timedelta
from functools import total_ordering
from typing import Any, Self

import discord
from cached_property import cached_property
from cashews import Cache
from dacite import from_dict

from pylav.exceptions.track import TrackNotFoundException
from pylav.players.tracks.decoder import async_decoder

CACHE = Cache(name="TrackCache")
CACHE.setup("mem://?check_interval=10&size=10000")


@total_ordering
class Track:
    __slots__ = (
        "_node",
        "_is_partial",
        "_query",
        "_extra",
        "_unique_id",
        "__clear_cache_task",
        "_skip_segments",
        "_requester_id",
        "_requester",
        "_updated_query",
        "_id",
        "_extra",
        "_encoded",
        "_raw_data",
    )

    def __init__(
        self,
        node: None,
        query: Query,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        **extra: Any,
    ) -> None:
        """This class should not be instantiated directly. Use :meth:`Track.build_track` instead."""
        self._encoded = None
        self._is_partial = False
        self._requester = requester
        self._node = node
        self._query = query
        self._extra = extra
        self._skip_segments = skip_segments or []
        self._unique_id = hashlib.md5()
        self._updated_query = None
        self._id = str(uuid.uuid4())
        self._raw_data = {}

        self._process_init()

    def __int__(self) -> int:
        return 0

    def __gt__(self, other: Any) -> bool:
        return False

    def __lt__(self, other: Any) -> bool:
        return False

    def __ge__(self, other: Any) -> bool:
        return True

    def __le__(self, other: Any) -> bool:
        return True

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Track):
            return self.unique_identifier == other.unique_identifier
        return NotImplemented

    def __ne__(self, other: Any) -> bool:
        x = self.__eq__(other)
        return not x if x is not NotImplemented else NotImplemented

    def __hash__(self):
        return hash((self.unique_identifier,))

    def __getitem__(self, name) -> Any:
        return super().__getattribute__(name)

    def __repr__(self) -> str:
        return f"<Track title={self.title} identifier={self.identifier}>"

    def _process_init(self):
        if self._requester is None:
            self._requester_id = self._node.node_manager.client.bot.user.id
        elif isinstance(self._requester, int):
            self._requester_id = self._requester
        else:
            self._requester_id = self._requester.id

        if "partial" in self._extra:
            self._is_partial = self._extra["partial"]

        if self._query is not None:
            self.timestamp = self.timestamp or self._query.start_time

        if self._skip_segments and self.source != "youtube":
            self._skip_segments = []

        self._extra.pop("track", None)

    @classmethod
    def build_track(
        cls,
        node: None,
        data: Self | LavalinkTrackObject | dict | str | None,
        query: Query,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        **extra: Any,
    ) -> Self:
        """Builds a track object from the given data.

        Parameters
        ----------
        node: None
            The node that the track is being built for.
        data: :class:`Track` | :class:`LavalinkTrackObject` | :class:`dict` | :class:`str` | None
            The data to build the track from.
        query: :class:`Query`
            The query that the track was built from.
        skip_segments: :class:`list`[:class:`str`]
            The segments to skip when playing the track.
        requester: :class:`discord.abc.User` | :class:`int`
            The user that requested the track.
        **extra: Any
            Extra data to add to the track.
        """

        # Check if data is a Track object and return it if it is
        if isinstance(data, cls):
            return data

        # Check if data is a LavalinkTrackObject and process it.
        if isinstance(data, LavalinkTrackObject):
            return cls._from_lavalink_track_object(node, data, query, skip_segments, requester, **extra)

        if isinstance(data, dict):
            return cls._from_mapping(node, data, query, skip_segments, requester, **extra)

        if data is None or (isinstance(data, str) and data == MISSING):
            return cls._from_query(node, query, skip_segments, requester, **extra)

        if isinstance(data, str):
            return cls._from_base64_string(node, data, query, skip_segments, requester, **extra)

        raise TypeError(f"Expected Track, LavalinkTrackObject, dict, or str, got {type(data).__name__}")

    @classmethod
    def _from_lavalink_track_object(
        cls,
        node: None,
        data: LavalinkTrackObject,
        query: Query,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        **extra: Any,
    ) -> Self:
        instance = cls(node, query, skip_segments, requester, **extra)
        instance._encoded = data.encoded
        instance._extra = extra
        instance._raw_data = extra.get("raw_data", {})
        instance._unique_id.update(instance._encoded.encode())
        instance._is_partial = False
        return instance

    @classmethod
    def _from_mapping(
        cls,
        node: None,
        data: dict[str, Any],
        query: Query,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        **extra: Any,
    ) -> Self:
        instance = cls(node, query, skip_segments, requester, **extra)
        instance._encoded = data.get("encoded", data["track"])
        instance._raw_data = data.get("raw_data", {}) or extra.get("raw_data", {})
        instance._unique_id.update(instance._encoded.encode())
        return instance

    @classmethod
    def _from_base64_string(
        cls,
        node: None,
        data: str,
        query: Query,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        **extra: Any,
    ) -> Self:

        instance = cls(node, query, skip_segments, requester, **extra)
        instance._encoded = data
        instance._extra = extra
        instance._raw_data = extra.get("raw_data", {})
        instance._unique_id.update(instance._encoded.encode())
        instance._is_partial = False
        return instance

    @classmethod
    def _from_query(
        cls,
        node: None,
        query: Query,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        **extra: Any,
    ) -> Self:
        instance = cls(node, query, skip_segments, requester, **extra)
        instance._extra = extra
        instance._raw_data = extra.get("raw_data", {})
        instance._is_partial = True
        return instance

    def _copy_with_extras(self, node: None, **extra: Any) -> Self:
        instance = self.__class__(node, None, None, None)
        instance._extra = {**self._extra, **extra}
        instance._encoded = self._encoded
        instance._raw_data = self._raw_data
        instance._unique_id = self._unique_id
        instance._is_partial = self._is_partial
        instance._query = self._query
        return instance

    @property
    def encoded(self) -> str | None:
        return self._encoded

    @property
    def timestamp(self) -> int:
        return self._extra.get("timestamp", 0)

    @timestamp.setter
    def timestamp(self, value: int):
        self._extra["timestamp"] = value

    @property
    def requester_id(self) -> int:
        return self._requester_id

    @property
    def requester(self) -> discord.User | None:
        return self._node.node_manager.client.bot.get_user(self.requester_id)

    @property
    def last_known_position(self) -> int:
        return self._extra.get("last_known_position", 0)

    @property
    def id(self) -> str:
        return self._id

    @cached_property
    def unique_identifier(self) -> str:
        return self._unique_id.hexdigest()

    @property
    def is_partial(self) -> bool:
        return self._is_partial or not self.encoded

    @last_known_position.setter
    def last_known_position(self, value: int):
        self._extra["last_known_position"] = value

    async def identifier(self) -> str | None:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).info.identifier

    async def is_seekable(self) -> bool:
        return False if self.is_partial else (await self.fetch_full_track_data()).info.isSeekable

    async def duration(self) -> int:
        return 0 if self.is_partial else (await self.fetch_full_track_data()).info.length

    length = duration

    async def stream(self) -> bool:
        return False if self.is_partial else (await self.fetch_full_track_data()).info.isStream

    async def title(self) -> str:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).info.title

    async def uri(self) -> str:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).info.uri

    async def author(self) -> str:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).info.author

    async def source(self) -> str:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).info.sourceName

    async def thumbnail(self) -> str | None:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).info.thumbnail

    async def isrc(self) -> str | None:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).info.isrc

    async def probe_info(self) -> str | None:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).info.probeInfo

    async def query(self) -> Query:
        if self.encoded and self._updated_query is None:
            self._updated_query = self._query = await Query.from_base64(self.encoded)
        return self._query

    async def is_clypit(self) -> bool:
        return (await self.query()).is_clypit

    async def is_getyarn(self) -> bool:
        return (await self.query()).is_getyarn

    async def is_mixcloud(self) -> bool:
        return (await self.query()).is_mixcloud

    async def is_ocremix(self) -> bool:
        return (await self.query()).is_ocremix

    async def is_pornhub(self) -> bool:
        return (await self.query()).is_pornhub

    async def is_reddit(self) -> bool:
        return (await self.query()).is_reddit

    async def is_soundgasm(self) -> bool:
        return (await self.query()).is_soundgasm

    async def is_tiktok(self) -> bool:
        return (await self.query()).is_tiktok

    async def is_spotify(self) -> bool:
        return (await self.query()).is_spotify

    async def is_apple_music(self) -> bool:
        return (await self.query()).is_apple_music

    async def is_bandcamp(self) -> bool:
        return (await self.query()).is_bandcamp

    async def is_youtube(self) -> bool:
        return (await self.query()).is_youtube

    async def is_youtube_music(self) -> bool:
        return (await self.query()).is_youtube_music

    async def is_soundcloud(self) -> bool:
        return (await self.query()).is_soundcloud

    async def is_twitch(self) -> bool:
        return (await self.query()).is_twitch

    async def is_http(self) -> bool:
        return (await self.query()).is_http

    async def is_local(self) -> bool:
        return (await self.query()).is_local

    async def is_niconico(self) -> bool:
        return (await self.query()).is_niconico

    async def is_vimeo(self) -> bool:
        return (await self.query()).is_vimeo

    async def is_search(self) -> bool:
        return (await self.query()).is_search

    async def is_album(self) -> bool:
        return (await self.query()).is_album

    async def is_playlist(self) -> bool:
        return (await self.query()).is_playlist

    async def is_single(self) -> bool:
        return (await self.query()).is_single

    async def is_speak(self) -> bool:
        return (await self.query()).is_speak

    async def is_gctts(self) -> bool:
        return (await self.query()).is_gctts

    async def is_deezer(self) -> bool:
        return (await self.query()).is_deezer

    async def requires_capability(self) -> str:
        return q.requires_capability if (q := await self.query()) else "youtube"

    async def query_identifier(self) -> str:
        return (await self.query()).query_identifier

    async def query_source(self) -> str:
        return (await self.query()).source

    async def mix_playlist_url(self) -> str | None:
        if not self.identifier:
            return
        if self.source == "youtube":
            return f"https://www.youtube.com/watch?v={self.identifier}&list=RD{self.identifier}"

    @CACHE(ttl=timedelta(minutes=10), key="user:{self.unique_identifier}")
    async def fetch_full_track_data(
        self,
    ) -> LavalinkTrackObject:
        if self.encoded:
            return await async_decoder(self.encoded)
        else:
            return await self.search()

    async def to_json(self) -> dict:
        """
        Returns a dict representation of this Track.
        Returns
        -------
        :class:`dict`
            The dict representation of this Track.
        """
        return {
            "encoded": self.encoded,
            "query": await self.query_identifier() if await self.query() else None,
            "requester": self.requester.id if self.requester else self.requester_id,
            "skip_segments": self._skip_segments,
            "extra": {
                "timestamp": self.timestamp,
                "last_known_position": self.last_known_position,
                "partial": self._is_partial,
            },
            "raw_data": self._raw_data,
        }

    async def search(self, player: Player, bypass_cache: bool = False) -> Self:
        self._query = await Query.from_string(self._query)
        response = await player.node.get_track(await self.query(), first=True, bypass_cache=bypass_cache)
        if not response or not response.tracks:
            raise TrackNotFoundException(f"No tracks found for query {await self.query_identifier()}")
        self._encoded = response.tracks[0].encoded
        self._unique_id = hashlib.md5()
        self._unique_id.update(self.encoded.encode())
        self._is_partial = False
        return self

    async def search_all(self, player: Player, requester: int, bypass_cache: bool = False) -> list[Track]:
        self._query = await Query.from_string(self._query)
        response = await player.node.get_track(
            await self.query(), bypass_cache=bypass_cache, first=self._query.is_search
        )
        if not response or not response.tracks:
            raise TrackNotFoundException(f"No tracks found for query {await self.query_identifier()}")
        return [
            Track.build_track(
                data=track, node=player.node, query=await Query.from_base64(track.encoded), requester=requester
            )
            for track in response.tracks
        ]
