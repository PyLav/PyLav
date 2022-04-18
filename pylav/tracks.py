from __future__ import annotations

import asyncio
import hashlib
import operator
import re
import struct
import uuid
from base64 import b64decode
from functools import total_ordering
from io import BytesIO
from typing import TYPE_CHECKING, Any

import aiohttp
import discord
from cached_property import cached_property_with_ttl

from pylav.exceptions import InvalidTrack
from pylav.query import Query
from pylav.utils import MISSING

if TYPE_CHECKING:
    from pylav.node import Node
    from pylav.player import Player

STREAM_TITLE: re.Pattern = re.compile(rb"StreamTitle='([^']*)';")


def read_utfm(utf_len: int, utf_bytes: bytes) -> str:
    chars = []
    count = 0

    while count < utf_len:
        c = utf_bytes[count] & 0xFF
        if c > 127:
            break

        count += 1
        chars.append(chr(c))

    while count < utf_len:
        c = utf_bytes[count] & 0xFF
        shift = c >> 4

        if 0 <= shift <= 7:
            count += 1
            chars.append(chr(c))
        elif 12 <= shift <= 13:
            count += 2
            if count > utf_len:
                raise UnicodeError("malformed input: partial character at end")
            char2 = utf_bytes[count - 1]
            if (char2 & 0xC0) != 0x80:
                raise UnicodeError(f"malformed input around byte {str(count)}")

            char_shift = ((c & 0x1F) << 6) | (char2 & 0x3F)
            chars.append(chr(char_shift))
        elif shift == 14:
            count += 3
            if count > utf_len:
                raise UnicodeError("malformed input: partial character at end")

            char2 = utf_bytes[count - 2]
            char3 = utf_bytes[count - 1]

            if (char2 & 0xC0) != 0x80 or (char3 & 0xC0) != 0x80:
                raise UnicodeError(f"malformed input around byte {str(count - 1)}")

            char_shift = ((c & 0x0F) << 12) | ((char2 & 0x3F) << 6) | ((char3 & 0x3F) << 0)
            chars.append(chr(char_shift))
        else:
            raise UnicodeError(f"malformed input around byte {str(count)}")

    return "".join(chars).encode("utf-16", "surrogatepass").decode("utf-16")


class DataReader:
    def __init__(self, ts):
        self._buf = BytesIO(b64decode(ts))

    def _read(self, count):
        return self._buf.read(count)

    def read_byte(self) -> bytes:
        return self._read(1)

    def read_boolean(self) -> bool:
        (result,) = struct.unpack("B", self.read_byte())
        return result != 0

    def read_unsigned_short(self) -> int:
        (result,) = struct.unpack(">H", self._read(2))
        return result

    def read_int(self) -> int:
        (result,) = struct.unpack(">i", self._read(4))
        return result

    def read_long(self) -> int:
        (result,) = struct.unpack(">Q", self._read(8))
        return result

    def read_utf(self) -> bytes:
        text_length = self.read_unsigned_short()
        return self._read(text_length)

    def read_utfm(self) -> str:
        text_length = self.read_unsigned_short()
        utf_string = self._read(text_length)
        return read_utfm(text_length, utf_string)


def decode_track(track: str) -> tuple[dict[str, str | dict[str, str | bool | int | None]], int]:
    """
    Decodes a base64 track string into an AudioTrack object.
    Parameters
    ----------
    track: :class:`str`
        The base64 track string.
    Returns
    -------
    :class:`AudioTrack`
    """
    reader = DataReader(track)

    flags = (reader.read_int() & 0xC0000000) >> 30
    version = struct.unpack("B", reader.read_byte()) if flags & 1 != 0 else 1

    title = reader.read_utfm()
    author = reader.read_utfm()
    length = reader.read_long()
    identifier = reader.read_utf().decode()
    is_stream = reader.read_boolean()
    uri = reader.read_utf().decode() if reader.read_boolean() else None
    source = reader.read_utf().decode()

    # Position
    _ = reader.read_long()

    track_object = {
        "track": track,
        "info": {
            "title": title,
            "author": author,
            "length": length,
            "identifier": identifier,
            "isStream": is_stream,
            "uri": uri,
            "isSeekable": not is_stream,
            "source": source,
        },
    }

    return track_object, version


@total_ordering
class AudioTrack:
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
        node: Node,
        data: AudioTrack | dict | str | None,
        query: Query | None = None,
        skip_segments: list | None = None,
        **extra: Any,
    ):
        self._node = node
        self.__clear_cache_task: asyncio.Task | None = None
        self.__clear_thumbnail_cache_task: asyncio.Task | None = None
        self._is_partial = False
        self._query = query
        self.skip_segments = skip_segments or []
        if data is None or (isinstance(data, str) and data == MISSING):
            self.track = None
            self._is_partial = True
            self.extra = {}
        if isinstance(data, dict):
            try:
                self.track = data["track"]
                self._raw_data = data.get("raw_data", {})
                self.extra = extra
            except KeyError as ke:
                (missing_key,) = ke.args
                raise InvalidTrack(f"Cannot build a track from partial data! (Missing key: {missing_key})") from None
        elif isinstance(data, AudioTrack):
            self.track = data.track
            self._is_partial = data._is_partial
            self.extra = {**data.extra, **extra}
            self._raw_data = data._raw_data
            self._query = data._query or self._query
        else:
            self.track = data
            self.extra = extra
            self._raw_data = {}
        self.extra["requester"] = self.extra.get("requester", self._node.node_manager.client.bot.user.id)
        self._id = None

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
    def unique_identifier(self) -> str:
        if not self.is_partial:
            return hashlib.md5(self.track.encode()).hexdigest()
        else:
            return hashlib.md5(uuid.uuid4().bytes).hexdigest()

    @property
    def is_partial(self) -> bool:
        return self._is_partial and not self.track

    @property
    def query(self) -> Query | None:
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
        return self.extra.get("requester", None)

    @property
    def requester(self) -> discord.User | None:
        return self._node.node_manager.client.bot.get_user(self.requester_id)

    @property
    def timestamp(self) -> int:
        return self.extra.get("timestamp", 0)

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
        return f"<AudioTrack title={self.title} identifier={self.identifier}>"

    def __eq__(self, other) -> bool:
        if isinstance(other, AudioTrack):
            return self.track == other.track
        return NotImplemented

    def __ne__(self, other) -> bool:
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self) -> hash:
        return hash(tuple(sorted([self.track, self.title, self.identifier, self.uri])))

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
            "query": self.query.query_identifier if self.query else None,
            "extra": {
                "requester": self.requester_id,
                "timestamp": self.timestamp,
            },
            "raw_data": self._raw_data,
        }

    async def clear_cache(self, timer: int, function_name: str) -> None:
        await asyncio.sleep(timer)
        del self.__dict__[function_name]

    async def search(self, player: Player) -> None:
        self._query = await Query.from_string(self.query)
        response = await player.node.get_tracks(self.query, first=True)
        self.track = response["track"]

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

    async def get_track_display_name(
        self, max_length: int = None, author: bool = True, unformatted: bool = False, with_url: bool = False
    ) -> str:
        if self.is_partial:
            return discord.utils.escape_markdown(await self.query.query_to_queue(max_length, partial=True))
        else:
            url_start = "[" if with_url else ""
            url_end = f"]({self.uri})" if with_url and self.uri else ""
            if unformatted:
                maybe_bold = ""
                url_start = url_end = ""
            else:
                maybe_bold = "**"
            unknown_author = self.author != "Unknown artist"
            unknown_title = self.title != "Unknown title"
            if not author:
                author_string = ""
            else:
                author_string = f" - {self.author}"

            if self.query and self.query.is_local:
                if not (unknown_title and unknown_author):
                    base = discord.utils.escape_markdown(f"{self.title}{author_string}")
                    if max_length:
                        return f"{maybe_bold}{url_start}{base[:max_length-7]}...{url_end}{maybe_bold}"
                    else:
                        return f"{maybe_bold}{url_start}{base}{url_end}{maybe_bold}" + discord.utils.escape_markdown(
                            f"\n{await self.query.query_to_string()} "
                        )
                elif not unknown_title:
                    base = discord.utils.escape_markdown(f"{self.title}")
                    if max_length:
                        return f"{maybe_bold}{url_start}{base[:max_length-7]}...{url_end}{maybe_bold}"
                    else:
                        return f"{maybe_bold}{url_start}{base}{url_end}{maybe_bold}" + discord.utils.escape_markdown(
                            f"\n{await self.query.query_to_string()} "
                        )
                else:
                    base = discord.utils.escape_markdown(await self.query.query_to_string(max_length))
                    if max_length:
                        return f"{maybe_bold}{url_start}{base[:max_length-7]}...{url_end}{maybe_bold}"
                    else:
                        return f"{maybe_bold}{url_start}{base}{url_end}{maybe_bold}"
            else:
                if self.stream and self.query.is_stream:
                    icy = await self._icyparser(self.uri)
                    if icy:
                        title = icy
                    else:
                        title = f"{self.title}{author_string}"
                elif self.author.lower() not in self.title.lower():
                    title = f"{self.title}{author_string}"
                else:
                    title = self.title
                title = discord.utils.escape_markdown(title)
                if max_length:
                    return f"{maybe_bold}{url_start}{title[:max_length-7]}...{url_end}{maybe_bold}"
                else:
                    return f"{maybe_bold}{url_start}{title}{url_end}{maybe_bold}"

    async def _icyparser(self, url: str) -> str | None:
        try:
            async with self._node.session.get(url, headers={"Icy-MetaData": "1"}) as resp:
                metaint = int(resp.headers["icy-metaint"])
                for _ in range(5):
                    await resp.content.readexactly(metaint)
                    metadata_length = struct.unpack("B", await resp.content.readexactly(1))[0] * 16
                    metadata = await resp.content.readexactly(metadata_length)
                    m = re.search(STREAM_TITLE, metadata.rstrip(b"\0"))
                    if m:
                        title = m.group(1)
                        if title:
                            title = title.decode("utf-8", errors="replace")
                            return title
                    else:
                        return None
        except (KeyError, aiohttp.ClientConnectionError, aiohttp.ClientResponseError):
            return None
