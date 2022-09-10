from __future__ import annotations

import asyncio
import hashlib
import operator
import re
import struct
import uuid
from functools import total_ordering
from typing import TYPE_CHECKING, Any

import asyncstdlib
import discord
from cached_property import cached_property, cached_property_with_ttl

from pylav._logging import getLogger
from pylav.exceptions import InvalidTrack, TrackNotFound
from pylav.query import Query
from pylav.track_encoding import decode_track
from pylav.utils import MISSING

if TYPE_CHECKING:
    from pylav.node import Node
    from pylav.player import Player

STREAM_TITLE: re.Pattern = re.compile(rb"StreamTitle='([^']*)';")
SQUARE_BRACKETS: re.Pattern = re.compile(r"[\[\]]")

LOGGER = getLogger("PyLav.tracks")


@total_ordering
class Track:
    """
    Represents the Track sent to Lavalink.
    Parameters
    ----------
    data: :class:`dict`
        The data to initialise an Track from.
    requester: :class:`any`
        The requester of the track.
    extra: :class:`dict`
        Any extra information to store in this Track.
    Attributes
    ----------
    track: :class:`str`
        The base64-encoded string representing a Lavalink-readable Track.
    identifier: :class:`str`
        The track's id. For example, a YouTube track's identifier will look like dQw4w9WgXcQ.
    is_seekable: :class:`bool`
        Whether the track supports seeking.
    author: :class:`str`
        The track's uploader.
    duration: :class:`int`
        The duration of the track, in milliseconds.
    stream: :class:`bool`
        Whether the track is a live-stream.
    title: :class:`str`
        The title of the track.
    uri: :class:`str`
        The full URL of track.
    extra: :class:`dict`
        Any extra properties given to this Track will be stored here.
    """

    __slots__ = (
        "_node",
        "_is_partial",
        "_query",
        "_unique_id",
        "_extra",
        "_raw_data",
        "_requester",
        "_id",
        "_updated_query",
        "__clear_cache_task",
        "__clear_thumbnail_cache_task",
        "track",
        "skip_segments",
        "extra",
        "__dict__",
    )

    def __init__(
        self,
        *,
        node: Node,
        data: Track | dict | str | None,
        query: Query,
        skip_segments: list | None = None,
        requester: int = None,
        **extra: Any,
    ):
        self._node = node
        self.__clear_cache_task: asyncio.Task | None = None
        self.__clear_thumbnail_cache_task: asyncio.Task | None = None
        self._is_partial = False
        self._query = query
        self.skip_segments = skip_segments or []
        self._unique_id = hashlib.md5()
        self._extra = extra
        if data is None or (isinstance(data, str) and data == MISSING):
            self.track = None
            self._is_partial = True
            if query is None:
                raise InvalidTrack("Cannot create a partial Track without a query")
            self._unique_id.update(query.query_identifier.encode())
            self.extra = {}
            self._raw_data = extra.get("raw_data", {})
        elif isinstance(data, dict):
            try:
                self.track = data["track"]
                self._raw_data = data.get("raw_data", {}) or extra.get("raw_data", {})
                self.extra = extra
                self._unique_id.update(self.track.encode())
            except KeyError as ke:
                (missing_key,) = ke.args
                raise InvalidTrack(f"Cannot build a track from partial data! (Missing key: {missing_key})") from None
        elif isinstance(data, Track):
            self.track = data.track
            self._is_partial = data._is_partial
            self.extra = {**data.extra, **extra}
            self._raw_data = data._raw_data
            self._query = data._query or self._query
            self._unique_id = data._unique_id
        elif isinstance(data, str):
            self.track = data
            self.extra = extra
            self._raw_data = extra.get("raw_data", {})
            self._unique_id.update(self.track.encode())  # type: ignore
        if self._query is not None:
            self.timestamp = self.timestamp or self._query.start_time
        self._requester = requester or self._node.node_manager.client.bot.user.id
        self._id = str(uuid.uuid4())
        self._updated_query = None

    @cached_property_with_ttl(ttl=60)
    def full_track(
        self,
    ) -> dict[str, str | dict[str, str | bool | int | None]]:
        if self.__clear_cache_task is not None and not self.__clear_cache_task.cancelled():
            self.__clear_cache_task.cancel()
        response, _ = (self._raw_data, None)
        if not response:
            response, _ = decode_track(self.track)
        self.__clear_cache_task = asyncio.create_task(self.clear_cache(65, "full_track"))
        return response

    @property
    def id(self) -> str:
        return self._id

    @cached_property
    def unique_identifier(self) -> str:
        return self._unique_id.hexdigest()

    @property
    def is_partial(self) -> bool:
        return self._is_partial and not self.track

    async def query(self) -> Query:
        if self.track and self._updated_query is None:
            self._updated_query = self._query = await Query.from_base64(self.track)
        return self._query

    @property
    def identifier(self) -> str | None:
        return MISSING if self.is_partial else self.full_track["info"]["identifier"]

    @property
    def is_seekable(self) -> bool:
        return MISSING if self.is_partial else self.full_track["info"]["isSeekable"]

    @property
    def duration(self) -> int:
        return MISSING if self.is_partial else self.full_track["info"]["length"]

    @property
    def stream(self) -> bool:
        return MISSING if self.is_partial else self.full_track["info"]["isStream"]

    @property
    def title(self) -> str:
        return MISSING if self.is_partial else self.full_track["info"]["title"]

    @property
    def uri(self) -> str:
        return MISSING if self.is_partial else self.full_track["info"]["uri"]

    @property
    def author(self) -> str:
        return MISSING if self.is_partial else self.full_track["info"]["author"]

    @property
    def source(self) -> str:
        return MISSING if self.is_partial else self.full_track["info"]["source"]

    @property
    def requester_id(self) -> int:
        return self._requester

    @property
    def requester(self) -> discord.User | None:
        return self._node.node_manager.client.bot.get_user(self.requester_id)

    @property
    def timestamp(self) -> int:
        return self.extra.get("timestamp", 0)

    @timestamp.setter
    def timestamp(self, value: int):
        self.extra["timestamp"] = value

    @property
    def last_known_position(self) -> int:
        return self.extra.get("last_known_position", 0)

    @last_known_position.setter
    def last_known_position(self, value: int):
        self.extra["last_known_position"] = value

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

    async def requires_capability(self) -> str:
        return q.requires_capability if (q := await self.query()) else "youtube"

    async def query_identifier(self) -> str:
        return (await self.query()).query_identifier

    async def query_source(self) -> str:
        return (await self.query()).source

    async def thumbnail(self) -> str | None:
        """Optional[str]: Returns a thumbnail URL for YouTube and Spotify tracks"""
        if not self.identifier:
            return
        if self.source == "youtube":
            return f"https://img.youtube.com/vi/{self.identifier}/mqdefault.jpg"
        elif self.source == "spotify":
            async with self._node.node_manager.client.spotify_client as sp_client:
                track = await sp_client.get_track(self.identifier)
                images = track.album.images
                image = await asyncstdlib.max(images, key=operator.attrgetter("width"))
                return image.url

    async def mix_playlist_url(self) -> str | None:
        if not self.identifier:
            return
        if self.source == "youtube":
            return f"https://www.youtube.com/watch?v={self.identifier}&list=RD{self.identifier}"

    def __getitem__(self, name) -> Any:
        return super().__getattribute__(name)

    def __repr__(self) -> str:
        return f"<Track title={self.title} identifier={self.identifier}>"

    async def to_json(self) -> dict:
        """
        Returns a dict representation of this Track.
        Returns
        -------
        :class:`dict`
            The dict representation of this Track.
        """
        return {
            "track": self.track,
            "query": await self.query_identifier() if await self.query() else None,
            "requester": self.requester.id if self.requester else self.requester_id,
            "skip_segments": self.skip_segments,
            "extra": {
                "timestamp": self.timestamp,
                "last_known_position": self.last_known_position,
            },
            "raw_data": self._raw_data,
        }

    async def clear_cache(self, timer: int, function_name: str) -> None:
        await asyncio.sleep(timer)
        del self.__dict__[function_name]

    async def search(self, player: Player, bypass_cache: bool = False) -> None:
        self._query = await Query.from_string(self._query)
        response = await player.node.get_tracks(await self.query(), first=True, bypass_cache=bypass_cache)
        if not response or "track" not in response:
            raise TrackNotFound(f"No tracks found for query {await self.query_identifier()}")
        self.track = response["track"]
        self._unique_id = hashlib.md5()
        self._unique_id.update(self.track.encode())
        if "unique_identifier" in self.__dict__:
            del self.__dict__["unique_identifier"]

    def __int__(self):
        return 0

    def __gt__(self, other):
        return False

    def __lt__(self, other):
        return False

    def __ge__(self, other):
        return True

    def __le__(self, other):
        return True

    def __eq__(self, other):
        if isinstance(other, Track):
            return self.unique_identifier == other.unique_identifier
        return NotImplemented

    def __ne__(self, other):
        x = self.__eq__(other)
        return not x if x is not NotImplemented else NotImplemented

    def __hash__(self):
        return hash((self.unique_identifier,))

    async def get_track_display_name(
        self, max_length: int = None, author: bool = True, unformatted: bool = False, with_url: bool = False
    ) -> str:  # sourcery skip: low-code-quality
        if self.is_partial:
            base = await (await self.query()).query_to_queue(max_length, partial=True)
            base = SQUARE_BRACKETS.sub("", base).strip()
            if max_length and len(base) > (actual_length := max_length - 1):
                base = f"{base[:actual_length]}" + "\N{HORIZONTAL ELLIPSIS}"
            return discord.utils.escape_markdown(base)
        else:
            length_to_trim = 7
            if unformatted:
                bold = ""
                url_start = url_end = ""
                length_to_trim = 3
            elif with_url:
                bold = "**"
                url_start = "["
                url_end = f"]({self.uri})"
            else:
                bold = "**"
                url_start = url_end = ""
            if max_length:
                max_length -= length_to_trim
            unknown_author = self.author != "Unknown artist"
            unknown_title = self.title != "Unknown title"
            author_string = f" - {self.author}" if author else ""
            if await self.query() and await self.is_local():
                url_start = url_end = ""
                if not (unknown_title and unknown_author):
                    base = f"{self.title}{author_string}"
                    base = SQUARE_BRACKETS.sub("", base).strip()
                    if max_length and len(base) > max_length:
                        base = base = "\N{HORIZONTAL ELLIPSIS}" + f"{base[-max_length:]}"
                    elif not max_length:
                        base += f"\n{await  (await self.query()).query_to_string(ellipsis=False)} "
                else:
                    base = await (await self.query()).query_to_string(max_length, name_only=True)
                    base = SQUARE_BRACKETS.sub("", base).strip()
            else:
                if self.stream:
                    icy = await self._icyparser(self.uri)
                    base = icy or f"{self.title}{author_string}"
                elif self.author.lower() not in self.title.lower():
                    base = f"{self.title}{author_string}"
                else:
                    base = self.title
                base = SQUARE_BRACKETS.sub("", base).strip()
                if max_length and len(base) > max_length:
                    base = f"{base[:max_length]}" + "\N{HORIZONTAL ELLIPSIS}"

            base = discord.utils.escape_markdown(base)
            return f"{bold}{url_start}{base}{url_end}{bold}"

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
        except Exception:
            return None
