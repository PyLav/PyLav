from __future__ import annotations

import pathlib
import re
from typing import TYPE_CHECKING, Literal

import aiopath
from red_commons.logging import getLogger

if TYPE_CHECKING:
    from pylav.localfiles import LocalFile

LOGGER = getLogger("red.PyLink.Query")

CLYPIT_REGEX = re.compile(r"(http://|https://(www.)?)?clyp\.it/(.*)", re.IGNORECASE)
GETYARN_REGEX = re.compile(r"(?:http://|https://(?:www.)?)?getyarn.io/yarn-clip/(.*)", re.IGNORECASE)
MIXCLOUD_REGEX = re.compile(
    r"https?://(?:(?:www|beta|m)\.)?mixcloud.com/([^/]+)/(?!stream|uploads|favorites|listens|playlists)([^/]+)/?",
    re.IGNORECASE,
)
OCRREMIX_PATTERN = re.compile(r"(?:https?://(?:www\.)?ocremix\.org/remix/)?(?P<id>OCR\d+)(?:.*)?", re.IGNORECASE)
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
SOUNDGASM_REGEX = re.compile(r"https?://soundgasm\.net/u/(?P<path>(?P<author>[^/]+)/[^/]+)", re.IGNORECASE)
TIKTOK_REGEX = re.compile(r"^https://(?:www\.|m\.)?tiktok\.com/@(?P<user>[^/]+)/video/(?P<video>\d+).*$", re.IGNORECASE)


SPOTIFY_REGEX = re.compile(
    r"(https?://)?(www\.)?open\.spotify\.com/(user/[a-zA-Z\d\\-_]+/)?"
    r"(?P<type>track|album|playlist|artist)/"
    r"(?P<identifier>[a-zA-Z\d\\-_]+)",
    re.IGNORECASE,
)

APPLE_MUSIC_REGEX = re.compile(
    r"(https?://)?(www\.)?music\.apple\.com/"
    r"(?P<countrycode>[a-zA-Z]{2}/)?"
    r"(?P<type>album|playlist|artist)(/[a-zA-Z\d\\-]+)?/"
    r"(?P<identifier>[a-zA-Z\d.]+)"
    r"(\?i=(?P<identifier2>\d+))?",
    re.IGNORECASE,
)

BANDCAMP_REGEX = re.compile(
    r"^(https?://(?:[^.]+\.|)bandcamp\.com)/(track|album)/([a-zA-Z\d\\-_]+)/?(?:\?.*|)$", re.IGNORECASE
)
NICONICO_REGEX = re.compile(r"(?:http://|https://|)(?:www\.|)nicovideo\.jp/watch/(sm\d+)(?:\?.*|)$", re.IGNORECASE)
TWITCH_REGEX = re.compile(r"^https://(?:www\.|go\.)?twitch\.tv/([^/]+)$", re.IGNORECASE)
VIMEO_REGEX = re.compile(r"^https://vimeo.com/\d+(?:\?.*|)$", re.IGNORECASE)

SOUND_CLOUD_REGEX = re.compile(
    r"^(?:http://|https://|)soundcloud\.app\.goo\.gl/([a-zA-Z\d\\-_]+)/?(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/([a-zA-Z\d\\-_]+)/([a-zA-Z\d\\-_]+)/?(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/([a-zA-Z\d\\-_]+)/"
    r"([a-zA-Z\d\\-_]+)/s-([a-zA-Z\d\\-_]+)(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/([a-zA-Z\d\\-_]+)/likes/?(?:\?.*|)$",
    re.IGNORECASE,
)

YOUTUBE_REGEX = re.compile(r"(?:http://|https://|)(?:www\.|)(?P<music>music\.)?youtu(be\.com|\.be)", re.IGNORECASE)
TTS_REGEX = re.compile(r"^(speak|tts):(.*)$", re.IGNORECASE)
GCTSS_REGEX = re.compile(r"^(tts://)(.*)$", re.IGNORECASE)
SEARCH_REGEX = re.compile(r"^(?P<source>ytm|yt|sp|sc|am)search:(?P<query>.*)$", re.IGNORECASE)
HTTP_REGEX = re.compile(r"^http(s)?://", re.IGNORECASE)

YOUTUBE_TIMESTAMP = re.compile(r"[&|?]t=(\d+)s?")
YOUTUBE_INDEX = re.compile(r"&index=(\d+)")
SPOTIFY_TIMESTAMP = re.compile(r"#(\d+):(\d+)")
SOUNDCLOUD_TIMESTAMP = re.compile(r"#t=(\d+):(\d+)s?")
TWITCH_TIMESTAMP = re.compile(r"\?t=(\d+)h(\d+)m(\d+)s")


def process_youtube(cls: type[Query], query: str, music: bool):
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
        query, "YouTube Music" if music else "YouTube", start_time=start_time, query_type=query_type, index=index
    )  # type: ignore


def process_spotify(cls: type[Query], query: str) -> Query:
    query_type = "single"
    if "/playlist/" in query:
        query_type = "playlist"
    elif "/album/" in query:
        query_type = "album"
    return cls(query, "Spotify", query_type=query_type)  # type: ignore


def process_soundcloud(cls: type[Query], query: str):
    if "/sets/" in query:
        if "?in=" in query:
            query_type = "single"
        else:
            query_type = "playlist"
    else:
        query_type = "single"
    return cls(query, "SoundCloud", query_type=query_type)  # type: ignore


def process_bandcamp(cls: type[Query], query: str) -> Query:
    if "/album/" in query:
        query_type = "album"
    else:
        query_type = "single"
    return cls(query, "Bandcamp", query_type=query_type)  # type: ignore


class Query:
    def __init__(
        self,
        query: str | aiopath.AsyncPath,
        source: str,
        search: bool = False,
        start_time=0,
        index=0,
        query_type: Literal["single", "playlist", "album"] = None,
    ):
        self._query = query
        self._source = source
        self._search = search
        self.start_time = start_time
        self.index = index
        self._type = query_type
        from pylav.localfiles import LocalFile

        self.__localfile_cls = LocalFile

    def __str__(self) -> str:
        return self.query_identifier

    @property
    def is_clypit(self) -> bool:
        return self.source == "Clyp"

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
        return self.source == "Soundgasm"

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
    def is_tts(self) -> bool:
        return self.source == "TTS" or self.is_gctts

    @property
    def is_gctts(self) -> bool:
        return self.source == "Google TTS"

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
            elif self.is_tts:
                if self.is_gctts:
                    return f"tts://{self._query}"
                return f"speak:{self._query}"
            else:
                return f"ytsearch:{self._query}"
        elif self.is_local:
            return f"{self._query}"
        return self._query

    @classmethod
    def __process_urls(cls, query: str) -> Query | None:
        if match := YOUTUBE_REGEX.match(query):
            music = match.group("music")
            return process_youtube(cls, query, music=bool(music))
        elif SPOTIFY_REGEX.match(query):
            return process_spotify(cls, query)
        elif APPLE_MUSIC_REGEX.match(query):
            return cls(query, "Apple Music")
        elif SOUND_CLOUD_REGEX.match(query):
            return process_soundcloud(cls, query)
        elif TWITCH_REGEX.match(query):
            return cls(query, "Twitch")
        elif GCTSS_REGEX.match(query):
            query = query.replace("tts://", "")
            return cls(query, "Google TTS", search=True)
        elif TTS_REGEX.match(query):
            query = query.replace("tts:", "").replace("speak:", "")
            return cls(query, "TTS", search=True)
        elif CLYPIT_REGEX.match(query):
            return cls(query, "Clyp")
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
            return cls(query, "Soundgasm")
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
            query = match.group("query")
            LOGGER.warning("%s", match.groups())
            if match.group("source") == "ytm":
                return cls(query, "YouTube Music", search=True)
            elif match.group("source") == "yt":
                return cls(query, "YouTube Music", search=True)
            elif match.group("source") == "sp":
                return cls(query, "Spotify", search=True)
            elif match.group("source") == "sc":
                return cls(query, "SoundCloud", search=True)
            elif match.group("source") == "am":
                return cls(query, "Apple Music", search=True)
            else:
                return cls(query, "YouTube Music", search=True)  # Fallback to YouTube

    @classmethod
    async def __process_local(cls, query: str | pathlib.Path | aiopath.AsyncPath) -> Query:
        path: aiopath.AsyncPath = aiopath.AsyncPath(query)
        path = await path.resolve()
        query_type = "single"
        if await path.is_dir():
            query_type = "album"
        if await path.exists():
            return cls(path.absolute(), "Local Files", query_type=query_type)  # type: ignore
        raise ValueError

    @classmethod
    async def from_string(cls, query: Query | str | pathlib.Path | aiopath.AsyncPath) -> Query:
        if isinstance(query, Query):
            return query
        if isinstance(query, pathlib.Path):
            return await cls.__process_local(query)
        elif query is None:
            raise ValueError("Query cannot be None")
        if output := cls.__process_urls(query):
            return output
        elif output := cls.__process_search(query):
            return output
        else:
            try:
                return await cls.__process_local(query)
            except Exception:
                return cls(query, "YouTube Music", search=True)  # Fallback to YouTube Music

    @classmethod
    def from_string_noawait(cls, query: Query | str) -> Query:
        """
        Same as from_string but without but non-awaitable - which makes it unable to process localtracks.
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

    async def query_to_string(self, max_length: int = None) -> str:
        if self.is_local:
            self._query: LocalFile = self.__localfile_cls(self._query)
            return await self._query.to_string_user(max_length)

        if max_length and len(self._query) > max_length:
            return self._query[: max_length - 3] + "..."

        return self._query

    async def query_to_queue(self, max_length: int = None, partial: bool = False) -> str:
        if partial:
            source = len(self.source) + 3
            if max_length:
                max_length -= source
            query_to_string = await self.query_to_string(max_length)
            return f"({self.source}) {query_to_string}"
        else:
            return await self.query_to_string(max_length)

    @property
    def source(self) -> str:
        return self._source

    @source.setter
    def source(self, source: str):
        if not self.is_search:
            raise ValueError("Source can only be set for search queries")

        source = source.lower()
        if source not in (allowed := {"ytm", "yt", "sp", "sc", "am", "local", "tts", "tts://"}):
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
        elif source == "tts":
            source = "TTS"
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
