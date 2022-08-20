from __future__ import annotations

import contextlib
import pathlib
import re
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Literal

import aiohttp
from discord.utils import maybe_coroutine

from pylav._logging import getLogger
from pylav.m3u8_parser._init__ import load as load_m3u8
from pylav.m3u8_parser.parser import is_url
from pylav.track_encoding import decode_track
from pylav.types import QueryT
from pylav.vendored import aiopath

if TYPE_CHECKING:
    from pylav.localfiles import LocalFile

LOGGER = getLogger("PyLav.Query")

CLYPIT_REGEX = re.compile(r"(http://|https://(www.)?)?clyp\.it/(.*)", re.IGNORECASE)
GETYARN_REGEX = re.compile(r"(?:http://|https://(?:www.)?)?getyarn.io/yarn-clip/(.*)", re.IGNORECASE)
MIXCLOUD_REGEX = re.compile(
    r"https?://(?:(?:www|beta|m)\.)?mixcloud.com/([^/]+)/(?!stream|uploads|favorites|listens|playlists)([^/]+)/?",
    re.IGNORECASE,
)
OCRREMIX_PATTERN = re.compile(r"(?:https?://(?:www\.)?ocremix\.org/remix/)?(?P<ocrmix_id>OCR\d+)(?:.*)?", re.IGNORECASE)
PORNHUB_REGEX = re.compile(
    r"^https?://([a-z]+.)?pornhub\.(com|net)/view_video\.php\?viewkey=([a-zA-Z\d]+).*$", re.IGNORECASE
)
REDDIT_REGEX = re.compile(
    r"https://(?:www|old)\.reddit\.com/"
    r"r/[^/]+/[^/]+/([^/]+)"
    r"(?:/?(?:[^/]+)?/?)?|"
    r"https://v\.redd\.it/([^/]+)(?:.*)?",
    re.IGNORECASE,
)
SOUNDGASM_REGEX = re.compile(
    r"https?://soundgasm\.net/u/(?P<soundgasm_path>(?P<soundgasm_author>[^/]+)/[^/]+)", re.IGNORECASE
)
TIKTOK_REGEX = re.compile(
    r"^https://(?:www\.|m\.)?tiktok\.com/@(?P<tiktok_user>[^/]+)/video/(?P<tiktok_video>\d+).*$", re.IGNORECASE
)


SPOTIFY_REGEX = re.compile(
    r"(https?://)?(www\.)?open\.spotify\.com/(user/[a-zA-Z\d\\-_]+/)?"
    r"(?P<spotify_type>track|album|playlist|artist)/"
    r"(?P<spotify_identifier>[a-zA-Z\d\\-_]+)",
    re.IGNORECASE,
)

APPLE_MUSIC_REGEX = re.compile(
    r"(https?://)?(www\.)?music\.apple\.com/"
    r"(?P<applemusic_countrycode>[a-zA-Z]{2}/)?"
    r"(?P<applemusic_type>album|playlist|artist)(/[a-zA-Z\d\\-]+)?/"
    r"(?P<applemusic_identifier>[a-zA-Z\d.]+)"
    r"(\?i=(?P<applemusic_identifier2>\d+))?",
    re.IGNORECASE,
)

BANDCAMP_REGEX = re.compile(
    r"^(https?://(?:[^.]+\.|)bandcamp\.com)/(track|album)/([a-zA-Z\d\\-_]+)/?(?:\?.*|)$", re.IGNORECASE
)
NICONICO_REGEX = re.compile(r"(?:http://|https://|)(?:www\.|)nicovideo\.jp/watch/(sm\d+)(?:\?.*|)$", re.IGNORECASE)
TWITCH_REGEX = re.compile(r"^https://(?:www\.|go\.)?twitch\.tv/([^/]+)$", re.IGNORECASE)
VIMEO_REGEX = re.compile(r"^https://vimeo.com/\d+(?:\?.*|)$", re.IGNORECASE)

SOUND_CLOUD_REGEX = re.compile(
    r"^(?:http://|https://|)soundcloud\.app\.goo\.gl/([a-zA-Z0-9-_]+)/?(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\\.|)(?:m\.|)soundcloud\.com/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/?(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/s-([a-zA-Z0-9-_]+)(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/([a-zA-Z0-9-_]+)/likes/?(?:\\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)(?:\?.*|)$",
    # This last line was manually added and does not exist in  in lavaplayer...
    #  https://github.com/Walkyst/lavaplayer-fork/blob/67bfdc4757947db61105c73628f2e4c2a7e4e992/main/src/main/java/com/sedmelluq/discord/lavaplayer/source/soundcloud/SoundCloudAudioSourceManager.java#L48
    re.IGNORECASE,
)
M3U_REGEX = re.compile(r"^.*\.m3u8?$", re.IGNORECASE)
PLS_REGEX = re.compile(r"^.*\.pls$", re.IGNORECASE)
PLS_TRACK_REGEX = re.compile(r"^File\d+=(?P<pls_query>.+)$", re.IGNORECASE)
XSPF_REGEX = re.compile(r"^.*\.xspf$", re.IGNORECASE)
PYLAV_REGEX = re.compile(r"^.*\.pylav$", re.IGNORECASE)

YOUTUBE_REGEX = re.compile(
    r"(?:http://|https://|)(?:www\.|)(?P<youtube_music>music\.)?youtu(be\.com|\.be)", re.IGNORECASE
)
SPEAK_REGEX = re.compile(r"^(?P<speak_source>speak):\s*?(?P<speak_query>.*)$", re.IGNORECASE)
GCTSS_REGEX = re.compile(r"^(?P<gctts_source>tts://)\s*?(?P<gctts_query>.*)$", re.IGNORECASE)
SEARCH_REGEX = re.compile(r"^(?P<search_source>ytm|yt|sp|sc|am)search:\s*?(?P<search_query>.*)$", re.IGNORECASE)
HTTP_REGEX = re.compile(r"^http(s)?://", re.IGNORECASE)

YOUTUBE_TIMESTAMP = re.compile(r"[&|?]t=(\d+)s?")
YOUTUBE_INDEX = re.compile(r"&index=(\d+)")
SPOTIFY_TIMESTAMP = re.compile(r"#(\d+):(\d+)")
SOUNDCLOUD_TIMESTAMP = re.compile(r"#t=(\d+):(\d+)s?")
TWITCH_TIMESTAMP = re.compile(r"\?t=(\d+)h(\d+)m(\d+)s")

LOCAL_TRACK_NESTED = re.compile(
    r"^(?P<local_recursive>all|nested|recursive|tree):\s*?(?P<local_query>.*)$", re.IGNORECASE
)
LOCAL_TRACK_URI_REGEX = re.compile(r"^file://(?P<local_file>.*)$", re.IGNORECASE)
BASE64_TEST_REGEX = re.compile(r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$")
MAX_RECURSION_DEPTH = 5  # Maximum depth of recursive searches for custom playlists (pls, m3u, xspf, pylav)

MERGED_REGEX = re.compile(
    "|".join(
        [
            r.pattern
            for r in [
                SPOTIFY_REGEX,
                APPLE_MUSIC_REGEX,
                YOUTUBE_REGEX,
                SPEAK_REGEX,
                GCTSS_REGEX,
                SEARCH_REGEX,
                CLYPIT_REGEX,
                GETYARN_REGEX,
                MIXCLOUD_REGEX,
                OCRREMIX_PATTERN,
                PORNHUB_REGEX,
                REDDIT_REGEX,
                SOUNDGASM_REGEX,
                TIKTOK_REGEX,
                BANDCAMP_REGEX,
                NICONICO_REGEX,
                TWITCH_REGEX,
                VIMEO_REGEX,
                SOUND_CLOUD_REGEX,
                M3U_REGEX,
                PLS_REGEX,
                PYLAV_REGEX,
                LOCAL_TRACK_NESTED,
                LOCAL_TRACK_URI_REGEX,
                HTTP_REGEX,
            ]
        ]
    ),
    re.IGNORECASE,
)


def process_youtube(cls: QueryT, query: str, music: bool):
    index = 0
    if match := YOUTUBE_TIMESTAMP.search(query):
        start_time = int(match.group(1))
    else:
        start_time = 0
    _has_index = "&index=" in query
    if _has_index and (match := YOUTUBE_INDEX.search(query)):
        index = int(match.group(1)) - 1
    if all(k in query for k in ["&list=", "watch?"]):
        query_type = "playlist"
        index = 0
    elif all(x in query for x in ["playlist?"]):
        query_type = "playlist"
    elif any(k in query for k in ["list="]):
        index = 0
        query_type = "single" if _has_index else "playlist"
    else:
        query_type = "single"
    return cls(
        query,
        "YouTube Music" if music else "YouTube",
        start_time=start_time,
        query_type=query_type,  # type: ignore
        index=index,
    )


def process_spotify(cls: QueryT, query: str) -> Query:
    query_type = "single"
    if "/playlist/" in query:
        query_type = "playlist"
    elif "/album/" in query:
        query_type = "album"
    return cls(query, "Spotify", query_type=query_type)


def process_soundcloud(cls: QueryT, query: str):
    if "/sets/" in query and "?in=" in query or "/sets/" not in query:
        query_type = "single"
    else:
        query_type = "playlist"
    return cls(query, "SoundCloud", query_type=query_type)


def process_bandcamp(cls: QueryT, query: str) -> Query:
    query_type = "album" if "/album/" in query else "single"
    return cls(query, "Bandcamp", query_type=query_type)


class Query:
    __localfile_cls: type[LocalFile] = None  # type: ignore

    def __init__(
        self,
        query: str | LocalFile,
        source: str,
        search: bool = False,
        start_time=0,
        index=0,
        query_type: Literal["single", "playlist", "album"] = None,
        recursive: bool = False,
    ):
        self._query = query
        self._source = source
        self._search = search
        self.start_time = start_time
        self.index = index
        self._type = query_type or "single"
        self._recursive = recursive
        from pylav.localfiles import LocalFile

        self.__localfile_cls = LocalFile

    def __str__(self) -> str:
        return self.query_identifier

    @property
    def is_clypit(self) -> bool:
        return self.source == "Clyp.it"

    @property
    def is_getyarn(self) -> bool:
        return self.source == "GetYarn"

    @property
    def is_mixcloud(self) -> bool:
        return self.source == "Mixcloud"

    @property
    def is_ocremix(self) -> bool:
        return self.source == "OverClocked ReMix"

    @property
    def is_pornhub(self) -> bool:
        return self.source == "Pornhub"

    @property
    def is_reddit(self) -> bool:
        return self.source == "Reddit"

    @property
    def is_soundgasm(self) -> bool:
        return self.source == "SoundGasm"

    @property
    def is_tiktok(self) -> bool:
        return self.source == "TikTok"

    @property
    def is_spotify(self) -> bool:
        return self.source == "Spotify"

    @property
    def is_apple_music(self) -> bool:
        return self.source == "Apple Music"

    @property
    def is_bandcamp(self) -> bool:
        return self.source == "Bandcamp"

    @property
    def is_youtube(self) -> bool:
        return self.source == "YouTube" or self.is_youtube_music

    @property
    def is_youtube_music(self) -> bool:
        return self.source == "YouTube Music"

    @property
    def is_soundcloud(self) -> bool:
        return self.source == "SoundCloud"

    @property
    def is_twitch(self) -> bool:
        return self.source == "Twitch"

    @property
    def is_http(self) -> bool:
        return self.source == "HTTP"

    @property
    def is_local(self) -> bool:
        return self.source == "Local Files"

    @property
    def is_niconico(self) -> bool:
        return self.source == "Niconico"

    @property
    def is_vimeo(self) -> bool:
        return self.source == "Vimeo"

    @property
    def is_search(self) -> bool:
        return self._search

    @property
    def is_album(self) -> bool:
        return self._type == "album"

    @property
    def is_playlist(self) -> bool:
        return self._type == "playlist"

    @property
    def is_single(self) -> bool:
        return self._type == "single"

    @property
    def is_speak(self) -> bool:
        return self.source == "speak"

    @property
    def is_gctts(self) -> bool:
        return self.source == "Google TTS"

    @property
    def is_m3u(self) -> bool:
        return self.source == "M3U"

    @property
    def is_pls(self) -> bool:
        return self.source == "PLS"

    @property
    def is_xspf(self) -> bool:
        return self.source == "XSPF"

    @property
    def is_pylav(self) -> bool:
        return self.source == "PyLav"

    @property
    def is_custom_playlist(self) -> bool:
        return any([self.is_pylav, self.is_m3u, self.is_pls, self.is_xspf])

    @property
    def invalid(self) -> bool:
        return self._query == "invalid" and self.source == "invalid"

    @property
    def query_identifier(self) -> str:
        if self.is_search:
            if self.is_youtube_music:
                return f"ytmsearch:{self._query}"
            elif self.is_youtube:
                return f"ytsearch:{self._query}"
            elif self.is_spotify:
                return f"spsearch:{self._query}"
            elif self.is_apple_music:
                return f"amsearch:{self._query}"
            elif self.is_soundcloud:
                return f"scsearch:{self._query}"
            elif self.is_speak:
                return f"speak:{self._query[:200]}"
            elif self.is_gctts:
                return f"tts://{self._query}"
            else:
                return f"ytsearch:{self._query}"
        elif self.is_local:
            return f"{self._query.path}"
        return self._query

    @classmethod
    def __process_urls(cls, query: str) -> Query | None:
        if match := YOUTUBE_REGEX.match(query):
            music = match.group("youtube_music")
            return process_youtube(cls, query, music=bool(music))
        elif SPOTIFY_REGEX.match(query):
            return process_spotify(cls, query)
        elif APPLE_MUSIC_REGEX.match(query):
            return cls(query, "Apple Music")
        elif SOUND_CLOUD_REGEX.match(query):
            return process_soundcloud(cls, query)
        elif TWITCH_REGEX.match(query):
            return cls(query, "Twitch")
        elif match := GCTSS_REGEX.match(query):
            query = match.group("gctts_query").strip()
            return cls(query, "Google TTS", search=True)
        elif match := SPEAK_REGEX.match(query):
            query = match.group("speak_query").strip()
            return cls(query, "speak", search=True)
        elif CLYPIT_REGEX.match(query):
            return cls(query, "Clyp.it")
        elif GETYARN_REGEX.match(query):
            return cls(query, "GetYarn")
        elif MIXCLOUD_REGEX.match(query):
            return cls(query, "Mixcloud")
        elif OCRREMIX_PATTERN.match(query):
            return cls(query, "OverClocked ReMix")
        elif PORNHUB_REGEX.match(query):
            return cls(query, "Pornhub")
        elif REDDIT_REGEX.match(query):
            return cls(query, "Reddit")
        elif SOUNDGASM_REGEX.match(query):
            return cls(query, "SoundGasm")
        elif TIKTOK_REGEX.match(query):
            return cls(query, "TikTok")
        elif BANDCAMP_REGEX.match(query):
            return process_bandcamp(cls, query)
        elif NICONICO_REGEX.match(query):
            return cls(query, "Niconico")
        elif VIMEO_REGEX.match(query):
            return cls(query, "Vimeo")
        elif HTTP_REGEX.match(query):
            return cls(query, "HTTP")

    @classmethod
    def __process_search(cls, query: str) -> Query | None:
        if match := SEARCH_REGEX.match(query):
            query = match.group("search_query").strip()
            if match.group("search_source") == "ytm":
                return cls(query, "YouTube Music", search=True)
            elif match.group("search_source") == "yt":
                return cls(query, "YouTube Music", search=True)
            elif match.group("search_source") == "sp":
                return cls(query, "Spotify", search=True)
            elif match.group("search_source") == "sc":
                return cls(query, "SoundCloud", search=True)
            elif match.group("search_source") == "am":
                return cls(query, "Apple Music", search=True)
            else:
                return cls(query, "YouTube Music", search=True)  # Fallback to YouTube

    @classmethod
    async def __process_local(cls, query: str | pathlib.Path | aiopath.AsyncPath) -> Query:
        if cls.__localfile_cls is None:
            from pylav.localfiles import LocalFile

            cls.__localfile_cls = LocalFile
        recursively = False
        query = f"{query}"
        if match := M3U_REGEX.match(query):
            return cls(query, "M3U", query_type="album")
        if match := LOCAL_TRACK_URI_REGEX.match(query):
            query = match.group("local_file").strip()
        elif match := LOCAL_TRACK_NESTED.match(query):
            recursively = bool(match.group("local_recursive"))
            query = match.group("local_query").strip()
        path: aiopath.AsyncPath = aiopath.AsyncPath(query)
        if not await path.exists():
            path_paths = path.parts[1:] if await maybe_coroutine(path.is_absolute) else path.parts
            path = cls.__localfile_cls._ROOT_FOLDER.joinpath(*path_paths)
            if not await path.exists():
                raise ValueError(f"{path} does not exist")
        try:
            local_path = cls.__localfile_cls(await maybe_coroutine(path.absolute))
            await local_path.initialize()
        except Exception as e:
            raise ValueError(f"{e}") from e
        query_type = "album" if await local_path.path.is_dir() else "single"
        return cls(local_path, "Local Files", query_type=query_type, recursive=recursively)  # type: ignore

    @classmethod
    async def __process_playlist(cls, query: str) -> Query:
        if __ := M3U_REGEX.match(query):
            return cls(query, "M3U", query_type="album")
        elif __ := PLS_REGEX.match(query):
            return cls(query, "PLS", query_type="album")
        # elif __ := XSPF_REGEX.match(query):
        #     return cls(query, "XSPF", query_type="album")
        elif __ := PYLAV_REGEX.match(query):
            return cls(query, "PyLav", query_type="album")

    @classmethod
    async def from_string(
        cls, query: Query | str | pathlib.Path | aiopath.AsyncPath, dont_search: bool = False
    ) -> Query:
        if isinstance(query, Query):
            return query
        if isinstance(query, pathlib.Path):
            try:
                return await cls.__process_local(query)
            except Exception:
                if dont_search:
                    return cls("invalid", "invalid")
                return cls(aiopath.AsyncPath(query), "YouTube Music", search=True)
        elif query is None:
            raise ValueError("Query cannot be None")
        source = None
        if len(query) > 20 and BASE64_TEST_REGEX.match(query):
            with contextlib.suppress(Exception):
                data, _ = decode_track(query)
                source = data["info"]["source"]
                query = data["info"]["uri"]
        if output := await cls.__process_playlist(query):
            if source:
                output._source = cls.__get_source_from_str(source)
            return output
        if (
            (output := cls.__process_urls(query))
            or not (output := cls.__process_urls(query))
            and (output := cls.__process_search(query))
        ):
            if source:
                output._source = cls.__get_source_from_str(source)
            return output
        else:
            try:
                output = await cls.__process_local(query)
                if source:
                    output._source = cls.__get_source_from_str(source)
                return output
            except Exception:
                if dont_search:
                    return cls("invalid", "invalid")
                output = cls(query, "YouTube Music", search=True)
                if source:
                    output._source = cls.__get_source_from_str(source)
                return output  # Fallback to YouTube Music

    @classmethod
    def from_string_noawait(cls, query: Query | str) -> Query:
        """
        Same as from_string but synchronous - which makes it unable to process localtracks.
        """
        if isinstance(query, Query):
            return query
        elif query is None:
            raise ValueError("Query cannot be None")
        if output := cls.__process_urls(query):
            return output
        elif output := cls.__process_search(query):
            return output
        else:
            return cls(query, "YouTube Music", search=True)  # Fallback to YouTube Music

    async def query_to_string(self, max_length: int = None, name_only: bool = False, ellipsis: bool = True) -> str:
        """
        Returns a string representation of the query.

        Parameters
        ----------
        max_length : int
            The maximum length of the string.
        name_only : bool
            If True, only the name of the query will be returned
            Only used for local tracks.
        ellipsis : bool
            Whether to format the string with ellipsis if it exceeds the max_length
        """

        if self.is_local:
            return await self._query.to_string_user(max_length, name_only=name_only, ellipsis=ellipsis)

        if max_length and len(self._query) > max_length:
            if ellipsis:
                return f"{self._query[: max_length - 3].strip()}..."
            else:
                return self._query[:max_length].strip()

        return self._query

    async def _yield_pylav_file_tracks(self) -> AsyncIterator[Query]:
        if self.is_pylav and self.is_album:
            file = aiopath.AsyncPath(self._query)
            if await file.exists():
                async with file.open("r") as f:
                    contents = await f.read()
                    for line in contents.splitlines():
                        yield await Query.from_string(line.strip(), dont_search=True)
            elif is_url(self._query):
                async with aiohttp.ClientSession() as session:
                    async with session.get(self._query) as resp:
                        contents = await resp.text()
                        for line in contents.splitlines():
                            yield await Query.from_string(line.strip(), dont_search=True)

    async def _yield_local_tracks(self) -> AsyncIterator[Query]:
        if self.is_album:
            if self.is_local:
                op = self._query.files_in_tree if self._recursive else self._query.files_in_folder

                async for entry in op():
                    yield entry
        elif self.is_single:
            if self.is_local:
                yield self

    async def _yield_m3u_tracks(self) -> AsyncIterator[Query]:
        if self.is_m3u and self.is_album:
            m3u8 = await load_m3u8(None, uri=self._query)
            for track in m3u8.files:
                yield await Query.from_string(track, dont_search=True)
            for playlist in m3u8.playlists:
                yield await Query.from_string(playlist.uri, dont_search=True)

    async def _yield_pls_tracks(self) -> AsyncIterator[Query]:
        if not self.is_pls or not self.is_album:
            return
        file = aiopath.AsyncPath(self._query)
        if await file.exists():
            async with file.open("r") as f:
                contents = await f.read()
                for line in contents.splitlines():
                    if match := PLS_TRACK_REGEX.match(line):
                        yield await Query.from_string(match.group("pls_query").strip(), dont_search=True)
        elif is_url(self._query):
            async with aiohttp.ClientSession() as session:
                async with session.get(self._query) as resp:
                    contents = await resp.text()
                    for line in contents.splitlines():
                        with contextlib.suppress(Exception):
                            if match := PLS_TRACK_REGEX.match(line):
                                yield await Query.from_string(match.group("pls_query").strip(), dont_search=True)

    async def _yield_xspf_tracks(self) -> AsyncIterator[Query]:
        if self.is_xspf:
            raise StopAsyncIteration

    async def _yield_tracks_recursively(self, query: Query, recursion_depth: int = 0) -> AsyncIterator[Query]:
        if query.invalid or recursion_depth > MAX_RECURSION_DEPTH:
            return
        recursion_depth += 1
        if query.is_m3u:
            async for m3u in query._yield_m3u_tracks():
                with contextlib.suppress(Exception):
                    async for q in self._yield_tracks_recursively(m3u, recursion_depth):
                        yield q
        elif query.is_pylav:
            async for pylav in query._yield_pylav_file_tracks():
                with contextlib.suppress(Exception):
                    async for q in self._yield_tracks_recursively(pylav, recursion_depth):
                        yield q
        elif query.is_pls:
            async for pls in query._yield_pls_tracks():
                with contextlib.suppress(Exception):
                    async for q in self._yield_tracks_recursively(pls, recursion_depth):
                        yield q
        elif query.is_local and query.is_album:
            async for local in query._yield_local_tracks():
                yield local
        else:
            yield query

    async def get_all_tracks_in_folder(self) -> AsyncIterator[Query]:
        if self.is_custom_playlist or self.is_local:
            async for track in self._yield_tracks_recursively(self, 0):
                if track.invalid:
                    continue
                yield track

    async def folder(self) -> str | None:
        if self.is_local:
            return self._query.parent.stem if await self._query.path.is_file() else self._query.name
        return None

    async def query_to_queue(self, max_length: int = None, partial: bool = False, name_only: bool = False) -> str:
        if not partial:
            return await self.query_to_string(max_length, name_only=name_only)
        source = len(self.source) + 3
        if max_length:
            max_length -= source
        query_to_string = await self.query_to_string(max_length, name_only=name_only)
        return f"({self.source}) {query_to_string}"

    @property
    def source(self) -> str:
        return self._source

    @source.setter
    def source(self, source: str):
        if not self.is_search:
            raise ValueError("Source can only be set for search queries")

        source = source.lower()
        if source not in (allowed := {"ytm", "yt", "sp", "sc", "am", "local", "speak", "tts://"}):
            raise ValueError(f"Invalid source: {source} - Allowed: {allowed}")
        if source == "ytm":
            source = "YouTube Music"
        if source == "yt":
            source = "YouTube"
        elif source == "sp":
            source = "Spotify"
        elif source == "sc":
            source = "SoundCloud"
        elif source == "am":
            source = "Apple Music"
        elif source == "local":
            source = "Local Files"
        elif source == "speak":
            source = "speak"
        elif source == "tts://":
            source = "Google TTS"
        self._source = source

    def with_index(self, index: int) -> Query:
        return type(self)(
            query=self._query,
            source=self._source,
            search=self._search,
            start_time=self.start_time,
            index=index,
            query_type=self._type,
        )

    @classmethod
    async def from_base64(cls, base64_string: str) -> Query:
        data, _ = decode_track(base64_string)
        source = data["info"]["source"]
        url = data["info"]["uri"]
        response = await cls.from_string(url)
        response._source = cls.__get_source_from_str(source)
        return response

    @classmethod
    def __get_source_from_str(cls, source: str) -> str:
        if source == "spotify":
            return "Spotify"
        elif source == "youtube":
            return "YouTube Music"
        elif source == "soundcloud":
            return "SoundCloud"
        elif source == "applemusic":
            return "Apple Music"
        elif source == "local":
            return "Local Files"
        elif source == "speak":
            return "speak"
        elif source == "gcloud-tts":
            return "Google TTS"
        elif source == "http":
            return "HTTP"
        elif source == "twitch":
            return "Twitch"
        elif source == "vimeo":
            return "Vimeo"
        elif source == "bandcamp":
            return "Bandcamp"
        elif source == "mixcloud":
            return "Mixcloud"
        elif source == "getyarn":
            return "GetYarn"
        elif source == "ocremix":
            return "OverClocked ReMix"
        elif source == "reddit":
            return "Reddit"
        elif source == "clypit":
            return "Clyp.it"
        elif source == "pornhub":
            return "PornHub"
        elif source == "soundgasm":
            return "SoundGasm"
        elif source == "tiktok":
            return "TikTok"
        elif source == "niconico":
            return "Niconico"
        else:
            return "YouTube"

    @property
    def requires_capability(self) -> str:
        if self.is_spotify:
            return "spotify"
        elif self.is_apple_music:
            return "applemusic"
        elif self.is_youtube:
            return "youtube"
        elif self.is_soundcloud:
            return "soundcloud"
        elif self.is_local:
            return "local"
        elif self.is_twitch:
            return "twitch"
        elif self.is_bandcamp:
            return "bandcamp"
        elif self.is_http:
            return "http"
        elif self.is_speak:
            return "speak"
        elif self.is_gctts:
            return "gcloud-tts"
        elif self.is_getyarn:
            return "getyarn"
        elif self.is_clypit:
            return "clypit"
        elif self.is_pornhub:
            return "pornhub"
        elif self.is_reddit:
            return "reddit"
        elif self.is_ocremix:
            return "ocremix"
        elif self.is_tiktok:
            return "tiktok"
        elif self.is_mixcloud:
            return "mixcloud"
        elif self.is_soundgasm:
            return "soundgasm"
        elif self.is_vimeo:
            return "vimeo"
        else:
            return "youtube"
