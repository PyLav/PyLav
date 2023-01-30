from __future__ import annotations

import hashlib
import struct
import typing
import uuid
from functools import total_ordering
from typing import Any

import asyncstdlib
import discord
from cached_property import cached_property  # type: ignore
from cashews import Cache  # type: ignore

from pylav.constants.regex import SQUARE_BRACKETS, STREAM_TITLE
from pylav.exceptions.track import InvalidTrackException, TrackNotFoundException
from pylav.extension.flowery.lyrics import Error, Lyrics
from pylav.helpers.misc import MISSING
from pylav.nodes.api.responses.playlists import Info
from pylav.nodes.api.responses.track import Track as APITrack
from pylav.players.query.obj import Query
from pylav.type_hints.dict_typing import JSON_DICT_TYPE

if typing.TYPE_CHECKING:
    from pylav.core.client import Client
    from pylav.nodes.node import Node
    from pylav.players.player import Player


__CLIENT: Client | None = None


# noinspection SpellCheckingInspection
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
        "_processed",
    )
    __CLIENT: Client | None = None

    def __init__(
        self,
        node: Node,
        query: Query,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        **extra: Any,
    ) -> None:
        """This class should not be instantiated directly. Use :meth:`Track.build_track` instead."""
        self._encoded: str | None = None
        self._is_partial = False
        self._requester = requester
        self._node = node
        self._query = query
        self._extra = extra
        self._skip_segments = skip_segments or []
        self._unique_id = hashlib.md5()
        self._updated_query = None
        self._id = str(uuid.uuid4())
        self._raw_data: JSON_DICT_TYPE = {}
        self._processed: APITrack | None = None

        self._process_init()

    @property
    def client(self) -> Client:
        """Get the client"""
        global __CLIENT
        return self.__CLIENT or __CLIENT

    @classmethod
    def attach_client(cls, client: Client) -> None:
        global __CLIENT
        __CLIENT = cls.__CLIENT = client

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
            return self._id == other._id
        raise NotImplemented

    def __ne__(self, other: Any) -> bool:
        x = self.__eq__(other)
        return not x

    def __hash__(self):
        return hash((self.unique_identifier,))

    def __getitem__(self, name: str) -> Any:
        return super().__getattribute__(name)

    def __repr__(self) -> str:
        return f"<Track identifier={self._id} encoded={self.encoded}>"

    def _process_init(self) -> None:
        if self._requester is None:
            self._requester_id = self.client.bot.user.id
        elif isinstance(self._requester, int):
            self._requester_id = self._requester
        else:
            self._requester_id = self._requester.id

        if "partial" in self._extra:
            self._is_partial = self._extra["partial"]

        if self._query is not None:
            self.timestamp = self.timestamp or self._query.start_time

        self._extra.pop("track", None)

    @classmethod
    async def build_track(
        cls,
        node: Node,
        data: Track | APITrack | dict[str, Any] | str | None,
        query: Query | None,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        lazy: bool = False,
        **extra: Any,
    ) -> Track:
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
        lazy: :class:`bool`
            Whether to build decode via the bot or Lavalink
        **extra: Any
            Extra data to add to the track.
        """

        # Check if data is a Track object and return it if it is
        if isinstance(data, cls):
            return data

        # Check if data is a LavalinkTrackObject and process it.
        if isinstance(data, APITrack):
            return cls._from_lavalink_track_object(node, data, query, skip_segments, requester, **extra)

        if isinstance(data, dict):
            try:
                return cls._from_mapping(node, data, query, skip_segments, requester, **extra)
            except KeyError as ke:
                (missing_key,) = ke.args
                raise InvalidTrackException(
                    f"Cannot build a track from partial data! (Missing key: {missing_key})"
                ) from ke

        if data is None:
            return cls._from_query(node, query, skip_segments, requester, **extra)

        if isinstance(data, str):
            return await cls._from_base64_string(node, data, skip_segments, requester, lazy=lazy, **extra)

        raise TypeError(f"Expected Track, LavalinkTrackObject, dict, or str, got {type(data).__name__}")

    @classmethod
    def _from_lavalink_track_object(
        cls,
        node: Node,
        data: APITrack,
        query: Query,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        **extra: Any,
    ) -> Track:
        instance = cls(node, query, skip_segments, requester, **extra)
        instance._encoded = data.encoded
        instance._extra = extra
        instance._raw_data = extra.get("raw_data", {})
        instance._unique_id = hashlib.md5()
        instance._unique_id.update(instance._encoded.encode())
        instance._is_partial = False
        instance._processed = data
        return instance

    @classmethod
    def _from_mapping(
        cls,
        node: Node,
        data: dict[str, Any],
        query: Query,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        **extra: Any,
    ) -> Track:
        instance = cls(node, query, skip_segments, requester, **extra)
        instance._encoded = data["encoded"]
        instance._is_partial = not bool(data["encoded"])
        instance._raw_data = data.get("raw_data", {}) or extra.get("raw_data", {})
        if instance._encoded is None:
            raise InvalidTrackException("Cannot build a track from partial data! (Missing key: encoded)")
        instance._unique_id = hashlib.md5()
        instance._unique_id.update(instance._encoded.encode())
        return instance

    @classmethod
    async def _from_base64_string(
        cls,
        node: Node,
        data: str,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        lazy: bool = False,
        **extra: Any,
    ) -> Track:
        track_obj = await cls.__CLIENT.decode_track(data, raise_on_failure=True, lazy=lazy)
        query_obj = await Query.from_string(track_obj.info.uri)
        return cls._from_lavalink_track_object(
            node=node, data=track_obj, query=query_obj, skip_segments=skip_segments, requester=requester, **extra
        )

    @classmethod
    def _from_query(
        cls,
        node: Node,
        query: Query,
        skip_segments: list[str] | None = None,
        requester: discord.abc.User | int | None = None,
        **extra: Any,
    ) -> Track:
        instance = cls(node, query, skip_segments, requester, **extra)
        instance._extra = extra
        instance._raw_data = extra.get("raw_data", {})
        instance._is_partial = True
        return instance

    def _copy_with_extras(self, node: Node, **extra: Any) -> Track:
        instance = self.__class__(node, self._query, None, None)
        instance._extra = {**self._extra, **extra}
        instance._encoded = self._encoded
        instance._raw_data = self._raw_data
        instance._unique_id = self._unique_id
        instance._is_partial = self._is_partial
        instance._processed = self._processed
        return instance

    @property
    def skip_segments(self) -> list[str]:
        """The segments to skip when playing the track."""
        return self._skip_segments

    @property
    def encoded(self) -> str | None:
        return self._encoded

    @property
    def timestamp(self) -> int:
        return self._extra.get("timestamp", 0)

    @timestamp.setter
    def timestamp(self, value: int) -> None:
        self._extra["timestamp"] = value

    @property
    def requester_id(self) -> int:
        return self._requester_id

    @property
    def requester(self) -> discord.User | None:
        return self.client.bot.get_user(self.requester_id)

    @property
    def last_known_position(self) -> int:
        return self._extra.get("last_known_position", 0)

    @last_known_position.setter
    def last_known_position(self, value: int) -> None:
        self._extra["last_known_position"] = value

    @property
    def id(self) -> str:
        return self._id

    @property
    def unique_identifier(self) -> str:
        return self._unique_id.hexdigest()

    @property
    def is_partial(self) -> bool:
        return bool(self._is_partial and not self.encoded)

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

    async def artworkUrl(self) -> str | None:  # noqa:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).info.artworkUrl

    async def isrc(self) -> str | None:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).info.isrc

    async def info(self) -> Info | None:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).info

    async def probe_info(self) -> str | None:
        return MISSING if self.is_partial else (await self.fetch_full_track_data()).pluginInfo.probeInfo

    async def query(self) -> Query:
        if self._processed and self._updated_query is None:
            self._updated_query = await Query.from_string(self._processed.info.uri)
            if self._query:
                self._updated_query.merge(
                    query=self._query,
                    start_time=True,
                    index=True,
                    source=True,
                    recursive=True,
                    search=True,
                )
            self._query = self._updated_query
            self.timestamp = self.timestamp or self._query.start_time
        if self.encoded and self._updated_query is None:
            assert self.encoded is not None
            self._updated_query = await Query.from_base64(self.encoded, lazy=True)
            if self._query:
                self._updated_query.merge(
                    query=self._query,
                    start_time=True,
                    index=True,
                    source=True,
                    recursive=True,
                    search=True,
                )
            self._query = self._updated_query
            self.timestamp = self.timestamp or self._query.start_time
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
        if not await self.identifier():
            return None
        if await self.source() == "youtube":
            return f"https://www.youtube.com/watch?v={self.identifier}&list=RD{self.identifier}"
        return None

    async def fetch_full_track_data(
        self,
    ) -> APITrack:
        if self._processed:
            return self._processed
        if self.encoded:
            self._processed = await self.client.decode_track(self.encoded)
        else:
            await self.search()
        return self._processed

    async def to_dict(self) -> dict[str, Any]:
        """
        Returns a dict representation of this Track.
        Returns
        -------
        :class:`dict`
            The dict representation of this Track.
        """
        return {
            "encoded": self.encoded,
            "query": await self.query_identifier(),
            "requester": self.requester.id if self.requester else self.requester_id,
            "skip_segments": self._skip_segments,
            "extra": {
                "timestamp": self.timestamp,
                "last_known_position": self.last_known_position,
                "partial": self._is_partial,
            },
            "raw_data": self._raw_data,
        }

    async def search(self, bypass_cache: bool = False):
        _query = await Query.from_string(self._query)
        _query.merge(
            query=self._query,
            start_time=True,
            index=True,
            source=True,
            recursive=True,
            search=True,
        )
        self._query = _query
        self.timestamp = self.timestamp or self._query.start_time
        response = await self.client._get_tracks(await self.query(), first=True, bypass_cache=bypass_cache)
        if not response or not response.tracks:
            raise TrackNotFoundException(f"No tracks found for query {await self.query_identifier()}")
        track = response.tracks[0]
        self._encoded = track.encoded
        assert isinstance(self._encoded, str)
        self._unique_id = hashlib.md5()
        self._unique_id.update(self.encoded.encode())
        self._is_partial = False
        self._processed = track

    async def search_all(self, player: Player, requester: int, bypass_cache: bool = False) -> list[Track]:
        _query = await Query.from_string(self._query)
        _query.merge(
            query=self._query,
            start_time=True,
            index=True,
            source=True,
            recursive=True,
            search=True,
        )
        self._query = _query
        response = await player.node.get_track(
            await self.query(), bypass_cache=bypass_cache, first=self._query.is_search
        )
        if not response or not response.tracks:
            raise TrackNotFoundException(f"No tracks found for query {await self.query_identifier()}")
        return [
            await Track.build_track(data=track, node=player.node, query=self._query, requester=requester)
            for track in response.tracks
        ]

    async def _icyparser(self, url: str) -> str | None:
        try:
            async with self._node.session.get(url, headers={"Icy-MetaData": "1"}) as resp:
                metaint = int(resp.headers["icy-metaint"])
                async for __ in asyncstdlib.iter(range(5)):
                    await resp.content.readexactly(metaint)
                    metadata_length = struct.unpack("B", await resp.content.readexactly(1))[0] * 16
                    metadata = await resp.content.readexactly(metadata_length)
                    if not (m := STREAM_TITLE.search(metadata.rstrip(b"\0"))):
                        return None
                    if title := m.group(1):
                        title = title.decode("utf-8", errors="replace")
                        return title
        except Exception:  # noqa
            return None
        return None

    async def get_track_display_name(
        self,
        max_length: int | None = None,
        author: bool = True,
        unformatted: bool = False,
        with_url: bool = False,
        escape: bool = True,
    ) -> str:
        if unformatted:
            return await self.get_track_display_name_unformatted(max_length=max_length, author=author, escape=escape)
        else:
            return await self.get_track_display_name_formatted(
                max_length=max_length, author=author, with_url=with_url, escape=escape
            )

    async def get_track_display_name_unformatted(
        self,
        max_length: int | None = None,
        author: bool = True,
        escape: bool = True,
    ) -> str:
        if self.is_partial:
            track_name = await self.get_partial_track_display_name(max_length=max_length)
        else:
            track_name = await self.get_full_track_display_name(max_length=max_length, author=author)
        return self._maybe_escape_markdown(text=track_name, escape=escape)

    async def get_track_display_name_formatted(
        self,
        max_length: int | None = None,
        author: bool = True,
        with_url: bool = False,
        escape: bool = True,
    ) -> str:

        if self.is_partial:
            track_name = await self.get_partial_track_display_name(
                max_length=max_length if with_url and max_length is None else (max_length - 8)
            )
            track_name = self._maybe_escape_markdown(text=track_name, escape=escape)
            if with_url and (query := await self.query()):
                if not query.is_single and not query.is_custom_playlist and not query.is_local:
                    track_name = f"**[{track_name}]({query.query_identifier})**"
        else:
            track_name = await self.get_full_track_display_name(
                max_length=max_length if with_url and max_length is None else (max_length - 8), author=author
            )
            track_name = self._maybe_escape_markdown(text=track_name, escape=escape)
            if with_url and (query := await self.query()) and not query.is_local:
                track_name = f"**[{track_name}]({await self.uri()})**"

        return track_name

    async def get_partial_track_display_name(self, max_length: int | None = None) -> str:
        query = await self.query()
        track_name = await query.query_to_queue(max_length if max_length is None else (max_length - 1), partial=True)
        track_name = SQUARE_BRACKETS.sub("", track_name).strip()
        if max_length is not None and len(track_name) > (max_length - 1):
            max_length -= 1
            return f"{track_name[:max_length]}\N{HORIZONTAL ELLIPSIS}"
        return track_name

    async def get_full_track_display_name(self, max_length: int | None = None, author: bool = True) -> str:
        author_string = f" - {await self.author()}" if author else ""
        return (
            await self.get_local_query_track_display_name(
                max_length=max_length,
                author_string=author_string,
                unknown_author=await self.author() != "Unknown artist",
                unknown_title=await self.title() != "Unknown title",
            )
            if await self.query() and await self.is_local()
            else await self.get_external_query_track_display_name(max_length=max_length, author_string=author_string)
        )

    async def get_local_query_track_display_name(
        self,
        author_string: str,
        unknown_author: bool,
        unknown_title: bool,
        max_length: int | None = None,
    ) -> str:
        if not (unknown_title and unknown_author):
            track_name = f"{await self.title()}{author_string}"
            track_name = SQUARE_BRACKETS.sub("", track_name).strip()
            if max_length and len(track_name) > (max_length - 1):
                max_length -= 1
                track_name = f"{track_name[:max_length]}\N{HORIZONTAL ELLIPSIS}"
            elif not max_length:
                track_name += f"\n{await (await self.query()).query_to_string(add_ellipsis=False, no_extension=True)} "
        else:
            track_name = await (await self.query()).query_to_string(max_length, name_only=True, no_extension=True)
            track_name = SQUARE_BRACKETS.sub("", track_name).strip()
        return track_name

    async def get_external_query_track_display_name(self, author_string: str, max_length: int | None = None) -> str:
        title = await self.title()

        if await self.stream():
            icy = await self._icyparser(await self.uri())
            track_name = icy or f"{title}{author_string}"
        elif (await self.author()).lower() not in title.lower():
            track_name = f"{title}{author_string}"
        else:
            track_name = title

        track_name = SQUARE_BRACKETS.sub("", track_name).strip()
        if max_length is not None and len(track_name) > (max_length - 1):
            max_length -= 1
            return f"{track_name[:max_length]}\N{HORIZONTAL ELLIPSIS}"
        return track_name

    @staticmethod
    def _maybe_escape_markdown(text: str, escape: bool = True) -> str:
        return discord.utils.escape_markdown(text) if escape else text

    async def fetch_lyrics(self) -> tuple[bool, Lyrics | Error | None]:
        if isrc := await self.isrc():
            return True, await self.client.flowery_api.lyrics.get_lyrics(isrc=isrc)
        elif not self.is_partial:
            if await self.is_spotify():
                return True, await self.client.flowery_api.lyrics.get_lyrics(spotify_id=await self.identifier())
            elif await self.source() in {"deezer", "applemusic"}:
                return True, await self.client.flowery_api.lyrics.get_lyrics(
                    query=f"{await self.title()} artist:{await self.author()}"
                )
            else:
                return False, await self.client.flowery_api.lyrics.get_lyrics(query=await self.title())
        return False, None
