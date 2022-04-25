from __future__ import annotations

import asyncio
import hashlib
import operator
import re
import struct
import uuid
from functools import total_ordering
from typing import TYPE_CHECKING, Any

import discord
from cached_property import cached_property, cached_property_with_ttl
from piccolo.utils.sync import run_sync
from red_commons.logging import getLogger

from pylav.exceptions import InvalidTrack, TrackNotFound
from pylav.query import Query
from pylav.track_encoding import decode_track
from pylav.utils import MISSING

if TYPE_CHECKING:
    from pylav.node import Node
    from pylav.player import Player

STREAM_TITLE: re.Pattern = re.compile(rb"StreamTitle='([^']*)';")
SQUARE_BRACKETS: re.Pattern = re.compile(r"[\[\]]")

LOGGER = getLogger("red.PyLink.tracks")


@total_ordering
class Track:
    """
    Represents the AudioTrack sent to Lavalink.
    Parameters
    ----------
    data: :class:`dict`
        The data to initialise an AudioTrack from.
    requester: :class:`any`
        The requester of the track.
    extra: :class:`dict`
        Any extra information to store in this AudioTrack.
    Attributes
    ----------
    track: :class:`str`
        The base64-encoded string representing a Lavalink-readable AudioTrack.
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
        Any extra properties given to this AudioTrack will be stored here.
    """

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
                raise InvalidTrack("Cannot create a partial Track without a query.")
            self._unique_id.update(query.query_identifier.encode())
            self.extra = {}
            self._raw_data = {}
        elif isinstance(data, dict):
            try:
                self.track = data["track"]
                self._raw_data = data.get("raw_data", {})
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
            self._raw_data = {}
            self._unique_id.update(self.track.encode())  # type: ignore
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

    @property
    def query(self) -> Query:
        if self.track and self._updated_query is None:
            self._updated_query = self._query = run_sync(Query.from_base64(self.track))
        return self._query

    @property
    def identifier(self) -> str | None:
        if self.is_partial:
            return MISSING
        return self.full_track["info"]["identifier"]

    @property
    def is_seekable(self) -> bool:
        if self.is_partial:
            return MISSING
        return self.full_track["info"]["isSeekable"]

    @property
    def duration(self) -> int:
        if self.is_partial:
            return MISSING
        return self.full_track["info"]["length"]

    @property
    def stream(self) -> bool:
        if self.is_partial:
            return MISSING
        return self.full_track["info"]["isStream"]

    @property
    def title(self) -> str:
        if self.is_partial:
            return MISSING
        return self.full_track["info"]["title"]

    @property
    def uri(self) -> str:
        if self.is_partial:
            return MISSING
        return self.full_track["info"]["uri"]

    @property
    def author(self) -> str:
        if self.is_partial:
            return MISSING
        return self.full_track["info"]["author"]

    @property
    def source(self) -> str:
        if self.is_partial:
            return MISSING
        return self.full_track["info"]["source"]

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
    def is_clypit(self) -> bool:
        return self.query.is_clypit

    @property
    def is_getyarn(self) -> bool:
        return self.query.is_getyarn

    @property
    def is_mixcloud(self) -> bool:
        return self.query.is_mixcloud

    @property
    def is_ocremix(self) -> bool:
        return self.query.is_ocremix

    @property
    def is_pornhub(self) -> bool:
        return self.query.is_pornhub

    @property
    def is_reddit(self) -> bool:
        return self.query.is_reddit

    @property
    def is_soundgasm(self) -> bool:
        return self.query.is_soundgasm

    @property
    def is_tiktok(self) -> bool:
        return self.query.is_tiktok

    @property
    def is_spotify(self) -> bool:
        return self.query.is_spotify

    @property
    def is_apple_music(self) -> bool:
        return self.query.is_apple_music

    @property
    def is_bandcamp(self) -> bool:
        return self.query.is_bandcamp

    @property
    def is_youtube(self) -> bool:
        return self.query.is_youtube

    @property
    def is_youtube_music(self) -> bool:
        return self.query.is_youtube_music

    @property
    def is_soundcloud(self) -> bool:
        return self.query.is_soundcloud

    @property
    def is_twitch(self) -> bool:
        return self.query.is_twitch

    @property
    def is_http(self) -> bool:
        return self.query.is_http

    @property
    def is_local(self) -> bool:
        return self.query.is_local

    @property
    def is_niconico(self) -> bool:
        return self.query.is_niconico

    @property
    def is_vimeo(self) -> bool:
        return self.query.is_vimeo

    @property
    def is_search(self) -> bool:
        return self.query.is_search

    @property
    def is_album(self) -> bool:
        return self.query.is_album

    @property
    def is_playlist(self) -> bool:
        return self.query.is_playlist

    @property
    def is_single(self) -> bool:
        return self.query.is_single

    @property
    def is_speak(self) -> bool:
        return self.query.is_speak

    @property
    def is_gctts(self) -> bool:
        return self.query.is_gctts

    @property
    def requires_capability(self) -> str:
        return self.query.requires_capability

    @property
    def query_identifier(self) -> str:
        return self.query.query_identifier

    async def thumbnail(self) -> str | None:
        """Optional[str]: Returns a thumbnail URL for YouTube and Spotify tracks."""
        if not self.identifier:
            return
        if self.source == "youtube":
            return f"https://img.youtube.com/vi/{self.identifier}/mqdefault.jpg"
        elif self.source == "spotify":
            async with self._node.node_manager.client.spotify_client as sp_client:
                track = await sp_client.get_track(self.identifier)
                images = track.album.images
                image = max(images, key=operator.attrgetter("width"))
                return image.url

    def __getitem__(self, name) -> Any:
        return super().__getattribute__(name)

    def __repr__(self) -> str:
        return (
            f"<AudioTrack title={self.title} identifier={self.identifier} "
            f"query={self.query_identifier if self.query else 'N/A'}>"
        )

    def to_json(self) -> dict:
        """
        Returns a dict representation of this AudioTrack.
        Returns
        -------
        :class:`dict`
            The dict representation of this AudioTrack.
        """
        return {
            "track": self.track,
            "query": self.query_identifier if self.query else None,
            "requester": self.requester_id,
            "extra": {
                "timestamp": self.timestamp,
            },
            "raw_data": self._raw_data,
        }

    async def clear_cache(self, timer: int, function_name: str) -> None:
        await asyncio.sleep(timer)
        del self.__dict__[function_name]

    async def search(self, player: Player, bypass_cache: bool = False) -> None:
        self._query = await Query.from_string(self._query)
        response = await player.node.get_tracks(self.query, first=True, bypass_cache=bypass_cache)
        if not response or "track" not in response:
            raise TrackNotFound(f"No tracks found for query {self.query_identifier}")
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
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self):
        return hash((self.unique_identifier,))

    async def get_track_display_name(
        self, max_length: int = None, author: bool = True, unformatted: bool = False, with_url: bool = False
    ) -> str:
        if self.is_partial:
            base = await self.query.query_to_queue(max_length, partial=True)
            base = SQUARE_BRACKETS.sub("", base).strip()
            if max_length and len(base) > (actual_length := max_length - 3):
                base = base[:actual_length] + "..."
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
            if not author:
                author_string = ""
            else:
                author_string = f" - {self.author}"

            if self.query and self.is_local:
                url_start = url_end = ""
                if not (unknown_title and unknown_author):
                    base = f"{self.title}{author_string}"
                    base = SQUARE_BRACKETS.sub("", base).strip()
                    if max_length and len(base) > max_length:
                        base = base = "..." + base[-max_length:]
                    elif not max_length:
                        base += f"\n{await self.query.query_to_string(ellipsis=False)} "
                    base = discord.utils.escape_markdown(base)
                    return f"{bold}{url_start}{base}{url_end}{bold}"
                elif not unknown_title:
                    base = self.title
                    base = SQUARE_BRACKETS.sub("", base).strip()
                    if max_length and len(base) > max_length:
                        base = base = "..." + base[-max_length:]
                    elif not max_length:
                        base += f"\n{await self.query.query_to_string(ellipsis=False)} "
                    base = discord.utils.escape_markdown(base)
                    return f"{bold}{url_start}{base}{url_end}{bold}"
                else:
                    base = await self.query.query_to_string(max_length, name_only=True)
                    base = SQUARE_BRACKETS.sub("", base).strip()
                    base = discord.utils.escape_markdown(base)
                    return f"{bold}{url_start}{base}{url_end}{bold}"
            else:
                if self.stream:
                    icy = await self._icyparser(self.uri)
                    if icy:
                        base = icy
                    else:
                        base = f"{self.title}{author_string}"
                elif self.author.lower() not in self.title.lower():
                    base = f"{self.title}{author_string}"
                else:
                    base = self.title
                base = SQUARE_BRACKETS.sub("", base).strip()
                if max_length and len(base) > max_length:
                    base = base[:max_length] + "..."
                base = discord.utils.escape_markdown(base)
                return f"{bold}{url_start}{base}{url_end}{bold}"

    async def _icyparser(self, url: str) -> str | None:
        try:
            async with self._node.session.get(url, headers={"Icy-MetaData": "1"}) as resp:
                metaint = int(resp.headers["icy-metaint"])
                for _ in range(5):
                    await resp.content.readexactly(metaint)
                    metadata_length = struct.unpack("B", await resp.content.readexactly(1))[0] * 16
                    metadata = await resp.content.readexactly(metadata_length)
                    m = STREAM_TITLE.search(metadata.rstrip(b"\0"))
                    if m:
                        title = m.group(1)
                        if title:
                            title = title.decode("utf-8", errors="replace")
                            return title
                    else:
                        return None
        except Exception:
            return None
