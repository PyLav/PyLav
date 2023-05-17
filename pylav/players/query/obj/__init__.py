from __future__ import annotations

import contextlib
import gzip
import pathlib
import typing
from collections.abc import AsyncIterator
from os import PathLike
from typing import Literal

import aiohttp
import aiopath  # type: ignore
import brotli  # type: ignore
import discord
import yaml

from pylav.compat import json
from pylav.constants import MAX_RECURSION_DEPTH
from pylav.constants.config import DEFAULT_SEARCH_SOURCE
from pylav.constants.node_features import SUPPORTED_SEARCHES
from pylav.constants.regex import (
    LOCAL_TRACK_NESTED,
    SOURCE_INPUT_MATCH_APPLE_MUSIC,
    SOURCE_INPUT_MATCH_BANDCAMP,
    SOURCE_INPUT_MATCH_BASE64_TEST,
    SOURCE_INPUT_MATCH_CLYPIT,
    SOURCE_INPUT_MATCH_DEEZER,
    SOURCE_INPUT_MATCH_GCTSS,
    SOURCE_INPUT_MATCH_GETYARN,
    SOURCE_INPUT_MATCH_HTTP,
    SOURCE_INPUT_MATCH_LOCAL_TRACK_URI,
    SOURCE_INPUT_MATCH_M3U,
    SOURCE_INPUT_MATCH_MIXCLOUD,
    SOURCE_INPUT_MATCH_NICONICO,
    SOURCE_INPUT_MATCH_OCRREMIX,
    SOURCE_INPUT_MATCH_PLS,
    SOURCE_INPUT_MATCH_PLS_TRACK,
    SOURCE_INPUT_MATCH_PORNHUB,
    SOURCE_INPUT_MATCH_PYLAV,
    SOURCE_INPUT_MATCH_REDDIT,
    SOURCE_INPUT_MATCH_SEARCH,
    SOURCE_INPUT_MATCH_SOUND_CLOUD,
    SOURCE_INPUT_MATCH_SOUNDGASM,
    SOURCE_INPUT_MATCH_SPEAK,
    SOURCE_INPUT_MATCH_SPOTIFY,
    SOURCE_INPUT_MATCH_TIKTOK,
    SOURCE_INPUT_MATCH_TWITCH,
    SOURCE_INPUT_MATCH_VIMEO,
    SOURCE_INPUT_MATCH_YANDEX,
    SOURCE_INPUT_MATCH_YOUTUBE,
)
from pylav.extension.m3u import load as m3u_loads
from pylav.players.query.local_files import LocalFile
from pylav.utils.validators import is_url

if typing.TYPE_CHECKING:
    from pylav.core.client import Client

__CLIENT: Client | None = None


# noinspection SpellCheckingInspection
class Query:
    __slots__ = (
        "_query",
        "_source",
        "_start_time",
        "_search",
        "start_time",
        "index",
        "_type",
        "_recursive",
        "_special_local",
        "_local_file_cls",
    )
    __local_file_cls: type[LocalFile] = LocalFile
    __CLIENT: Client | None = None

    def __init__(
        self,
        query: str | LocalFile,
        source: str,
        search: bool = False,
        start_time=0,
        index=0,
        query_type: Literal["single", "playlist", "album"] | None = None,
        recursive: bool = False,
        special_local: bool = False,
    ) -> None:
        self._query = query
        self._source = source
        self._search = search
        self.start_time = start_time * 1000
        self.index = index
        self._type = query_type or "single"
        self._recursive = recursive
        self._special_local = special_local

        self._local_file_cls = LocalFile
        self.update_local_file_cls(LocalFile)

    @property
    def client(self) -> Client:
        """Get the client"""
        global __CLIENT
        return self.__CLIENT or __CLIENT

    @classmethod
    def attach_client(cls, client: Client) -> None:
        global __CLIENT
        __CLIENT = cls.__CLIENT = client

    @classmethod
    def update_local_file_cls(cls, local_file_cls: type[LocalFile]) -> None:
        cls.__local_file_cls = local_file_cls

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            "query": self._query,
            "source": self._source,
            "search": self._search,
            "start_time": self.start_time,
            "index": self.index,
            "type": self._type,
            "recursive": self._recursive,
            "special_local": self._special_local,
        }

    def merge(
        self,
        query: Query,
        source: bool = False,
        search: bool = False,
        start_time: bool = False,
        index: bool = False,
        recursive: bool = False,
    ) -> None:
        if source and query:
            self._source = query.source
        if search and query:
            self._search = query._search
        if start_time and query:
            self.start_time = query.start_time
        if index and query:
            self.index = query.index
        if recursive and query:
            self._recursive = query._recursive

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
        return self.source == "Local" or (self._special_local and (self.is_m3u or self.is_pls or self.is_pylav))

    @property
    def is_niconico(self) -> bool:
        return self.source == "Niconico"

    @property
    def is_vimeo(self) -> bool:
        return self.source == "Vimeo"

    @property
    def is_deezer(self) -> bool:
        return self.source == "Deezer"

    @property
    def is_yandex_music(self) -> bool:
        return self.source == "Yandex Music"

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
            assert isinstance(self._query, str)
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
            elif self.is_deezer:
                return f"dzsearch:{self._query}"
            elif self.is_speak:
                return f"speak:{self._query[:200]}"
            elif self.is_gctts:
                return f"tts://{self._query}"
            elif self.is_yandex_music:
                return f"ymsearch:{self._query}"
            else:
                return f"{DEFAULT_SEARCH_SOURCE}:{self._query}"
        elif self.is_local:
            return f"{getattr(self._query, 'path', self._query)}"
        assert isinstance(self._query, str)
        return self._query

    @classmethod
    def __process_urls(cls, query: str) -> Query | None:  # sourcery skip: low-code-quality
        if match := SOURCE_INPUT_MATCH_YOUTUBE.match(query):
            music = match.group("youtube_music")
            return process_youtube(cls, query, music=bool(music))
        elif SOURCE_INPUT_MATCH_SPOTIFY.match(query):
            return process_spotify(cls, query)
        elif match := SOURCE_INPUT_MATCH_APPLE_MUSIC.match(query):
            return cls.process_applemusic(match, query)
        elif SOURCE_INPUT_MATCH_DEEZER.match(query):
            return process_deezer(cls, query)
        elif SOURCE_INPUT_MATCH_SOUND_CLOUD.match(query):
            return process_soundcloud(cls, query)
        elif SOURCE_INPUT_MATCH_TWITCH.match(query):
            return cls(query, "Twitch")
        elif match := SOURCE_INPUT_MATCH_GCTSS.match(query):
            query = match.group("gctts_query").strip()
            return cls(query, "Google TTS", search=True)
        elif match := SOURCE_INPUT_MATCH_SPEAK.match(query):
            query = match.group("speak_query").strip()
            return cls(query, "speak", search=True)
        elif SOURCE_INPUT_MATCH_CLYPIT.match(query):
            return cls(query, "Clyp.it")
        elif SOURCE_INPUT_MATCH_GETYARN.match(query):
            return cls(query, "GetYarn")
        elif match := SOURCE_INPUT_MATCH_MIXCLOUD.match(query):
            return cls.process_mixcloud(match, query)
        elif SOURCE_INPUT_MATCH_OCRREMIX.match(query):
            return cls(query, "OverClocked ReMix")
        elif SOURCE_INPUT_MATCH_PORNHUB.match(query):
            return cls(query, "Pornhub")
        elif SOURCE_INPUT_MATCH_REDDIT.match(query):
            return cls(query, "Reddit")
        elif SOURCE_INPUT_MATCH_SOUNDGASM.match(query):
            return cls(query, "SoundGasm")
        elif SOURCE_INPUT_MATCH_TIKTOK.match(query):
            return cls(query, "TikTok")
        elif SOURCE_INPUT_MATCH_BANDCAMP.match(query):
            return process_bandcamp(cls, query)
        elif SOURCE_INPUT_MATCH_NICONICO.match(query):
            return cls(query, "Niconico")
        elif SOURCE_INPUT_MATCH_VIMEO.match(query):
            return cls(query, "Vimeo")
        elif SOURCE_INPUT_MATCH_YANDEX.match(query):
            return process_yandex_music(cls, query)
        elif SOURCE_INPUT_MATCH_HTTP.match(query):
            return cls(query, "HTTP")
        return None

    @classmethod
    def process_applemusic(cls, match: typing.Match[str], query: str) -> Query:
        query_type = match.group("type")
        match query_type:
            case "album":
                if match.group("identifier2"):
                    return cls(query, "Apple Music", query_type="single")
                return cls(query, "Apple Music", query_type="album")
            case "song":
                return cls(query, "Apple Music", query_type="single")
            case __:
                return cls(query, "Apple Music", query_type="playlist")

    @classmethod
    def process_mixcloud(cls, match: typing.Match[str], query: str) -> Query:
        query_type = match.group("type")
        match query_type:
            case "uploads" | "favorites" | "listens":
                return cls(query, "Mixcloud", query_type="album")
            case "playlist":
                return cls(query, "Mixcloud", query_type="playlist")
            case __:
                return cls(query, "Mixcloud", query_type="single")

    @classmethod
    def __process_search(cls, query: str) -> Query | None:
        if match := SOURCE_INPUT_MATCH_SEARCH.match(query):
            query = match.group("search_query")
            deezer = (not query) and (query := match.group("search_deezer_isrc"))
            query = query.strip()
            if deezer:
                return cls(query, "Deezer", search=True)
            elif match.group("search_source") == "ytm":
                return cls(query, "YouTube Music", search=True)
            elif match.group("search_source") == "yt":
                return cls(query, "YouTube", search=True)
            elif match.group("search_source") == "sp":
                return cls(query, "Spotify", search=True)
            elif match.group("search_source") == "sc":
                return cls(query, "SoundCloud", search=True)
            elif match.group("search_source") == "am":
                return cls(query, "Apple Music", search=True)
            elif match.group("search_source") == "dz":
                return cls(query, "Deezer", search=True)
            elif match.group("search_source") == "ym":
                return cls(query, "Yandex Music", search=True)
            else:
                return cls(query, SUPPORTED_SEARCHES[DEFAULT_SEARCH_SOURCE], search=True)
        return None

    @classmethod
    async def __process_local_playlist(cls, query: str) -> LocalFile:
        # noinspection PyProtectedMember
        assert cls.__local_file_cls._ROOT_FOLDER is not None

        path: aiopath.AsyncPath = aiopath.AsyncPath(query)
        if not await path.exists():
            path_paths = typing.cast(
                list[str | PathLike[str]],
                path.parts[1:] if await discord.utils.maybe_coroutine(path.is_absolute) else path.parts,
            )
            # noinspection PyProtectedMember
            path = cls.__local_file_cls._ROOT_FOLDER.joinpath(*path_paths)
            if not await path.exists():
                raise ValueError(f"{path} does not exist")
        try:
            local_path = cls.__local_file_cls(await discord.utils.maybe_coroutine(path.absolute))
            await local_path.initialize()
        except Exception as e:
            raise ValueError(f"{e}") from e
        return local_path

    @classmethod
    async def __process_local(cls, query: str | pathlib.Path | aiopath.AsyncPath) -> Query:
        if cls.__local_file_cls is None:
            cls.__local_file_cls = LocalFile
        # noinspection PyProtectedMember
        assert cls.__local_file_cls._ROOT_FOLDER is not None
        recursively = False
        query = f"{query}"
        if playlist_cls := await cls.__process_playlist(query):
            return playlist_cls
        if match := SOURCE_INPUT_MATCH_LOCAL_TRACK_URI.match(query):
            query = match.group("local_file").strip()
        elif match := LOCAL_TRACK_NESTED.match(query):
            recursively = bool(match.group("local_recursive"))
            query = match.group("local_query").strip()
        path: aiopath.AsyncPath = aiopath.AsyncPath(query)
        if not await path.exists():
            path_paths = typing.cast(
                list[str | PathLike[str]],
                path.parts[1:] if await discord.utils.maybe_coroutine(path.is_absolute) else path.parts,
            )
            # noinspection PyProtectedMember
            path = cls.__local_file_cls._ROOT_FOLDER.joinpath(*path_paths)
            if not await path.exists():
                raise ValueError(f"{path} does not exist")
        try:
            local_path = cls.__local_file_cls(await discord.utils.maybe_coroutine(path.absolute))
            await local_path.initialize()
        except Exception as e:
            raise ValueError(f"{e}") from e
        query_type = "album" if await local_path.path.is_dir() else "single"
        return cls(local_path, "Local", query_type=query_type, recursive=recursively)  # type: ignore

    @classmethod
    async def __process_playlist(cls, query: str) -> Query | None:
        with contextlib.suppress(ValueError):
            url = is_url(query)
            query_final = query if url else await cls.__process_local_playlist(query)
            if __ := SOURCE_INPUT_MATCH_M3U.match(query):
                return cls(query_final, "M3U", query_type="album", special_local=not url)
            elif __ := SOURCE_INPUT_MATCH_PLS.match(query):
                return cls(query_final, "PLS", query_type="album", special_local=not url)
            elif __ := SOURCE_INPUT_MATCH_PYLAV.match(query):
                return cls(query_final, "PyLav", query_type="album", special_local=not url)
        return None

    @classmethod
    async def from_string(
        cls,
        query: Query | str | pathlib.Path | aiopath.AsyncPath,
        dont_search: bool = False,
        lazy: bool = False,
    ) -> Query:  # sourcery skip: low-code-quality
        if isinstance(query, Query):
            return query
        if isinstance(query, (aiopath.AsyncPath, pathlib.Path)):
            try:
                return await cls.__process_local(query)
            except Exception:  # noqa
                if dont_search:
                    return cls("invalid", "invalid")
                return cls(aiopath.AsyncPath(query), SUPPORTED_SEARCHES[DEFAULT_SEARCH_SOURCE], search=True)
        elif query is None:
            raise ValueError("Query cannot be None")
        source = None
        if len(query) > 20 and SOURCE_INPUT_MATCH_BASE64_TEST.match(query):
            with contextlib.suppress(Exception):
                data = await cls.__CLIENT.decode_track(query, raise_on_failure=True, lazy=lazy)
                source = data.info.sourceName
                query = data.info.uri
        try:
            if not dont_search and (output := await cls.__process_playlist(query)):
                if source:
                    output._source = cls.__get_source_from_str(source)
                return output
            if (output := cls.__process_urls(query)) or (output := cls.__process_search(query)):
                if source:
                    output._source = cls.__get_source_from_str(source)
                return output
            else:
                try:
                    if is_url(query):
                        raise ValueError
                    output = await cls.__process_local(query)
                    if source:
                        output._source = cls.__get_source_from_str(source)
                    return output
                except Exception:  # noqa
                    if dont_search:
                        return cls("invalid", "invalid")
                    output = cls(query, SUPPORTED_SEARCHES[DEFAULT_SEARCH_SOURCE], search=True)
                    if source:
                        output._source = cls.__get_source_from_str(source)
                    return output  # Fallback to Configured search source
        except Exception:  # noqa
            if dont_search:
                return cls("invalid", "invalid")
            output = cls(query, SUPPORTED_SEARCHES[DEFAULT_SEARCH_SOURCE], search=True)
            if source:
                output._source = cls.__get_source_from_str(source)
            return output  # Fallback to Configured search source

    @classmethod
    def from_string_noawait(cls, query: Query | str) -> Query:
        """
        Same as from_string but synchronous
        - which makes it unable to process localtracks, base64 queries or playlists (M3U, PLS, PyLav).
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
            return cls(query, SUPPORTED_SEARCHES[DEFAULT_SEARCH_SOURCE], search=True)

    async def query_to_string(
        self,
        max_length: int | None = None,
        name_only: bool = False,
        add_ellipsis: bool = True,
        with_emoji: bool = False,
        no_extension: bool = False,
    ) -> str:
        """
        Returns a string representation of the query.

        Parameters
        ----------
        max_length : int
            The maximum length of the string.
        name_only : bool
            If True, only the name of the query will be returned
            Only used for local tracks.
        add_ellipsis : bool
            Whether to format the string with ellipsis if it exceeds the max_length
        with_emoji : bool
            Whether to add an emoji to returned name if it is a local track.
        no_extension : bool
            Whether to remove the extension from the returned name if it is a local track.
        """

        if self.is_local:
            assert isinstance(self._query, self.__local_file_cls)
            return await self._query.to_string_user(
                max_length,
                name_only=name_only,
                add_ellipsis=add_ellipsis,
                with_emoji=with_emoji,
                no_extension=no_extension,
                is_album=self.is_album,
            )
        assert isinstance(self._query, str)
        if max_length and len(self._query) > max_length:
            if add_ellipsis:
                return f"{self._query[: max_length - 1].strip()}\N{HORIZONTAL ELLIPSIS}"
            else:
                return self._query[:max_length].strip()
        return self._query

    async def _yield_pylav_file_tracks(self) -> AsyncIterator[Query]:
        if not self.is_pylav or not self.is_album:
            return
        if self._special_local:
            assert isinstance(self._query, LocalFile)
            file = self._query.path
        else:
            file = aiopath.AsyncPath(self._query)
        if await file.exists():
            async with file.open("rb") as f:
                contents = await f.read()
                if ".gz" in file.suffixes:
                    contents = gzip.decompress(contents)
                elif ".br" in file.suffixes:
                    contents = brotli.decompress(contents)
                data_dict = typing.cast(dict[str, typing.Any], yaml.safe_load(contents))
                for track in iter(data_dict.get("tracks", [])):
                    yield await Query.from_base64(track)
        elif is_url(self._query):
            assert not isinstance(self._query, LocalFile)
            async with aiohttp.ClientSession(auto_decompress=False, json_serialize=json.dumps) as session:
                async with session.get(self._query) as response:
                    data = await response.read()
                    if ".gz.pylav" in self._query:
                        data = gzip.decompress(data)
                    elif ".br.pylav" in self._query:
                        data = brotli.decompress(data)
                    data_dict = typing.cast(dict[str, typing.Any], yaml.safe_load(data))
                    for track in iter(data_dict.get("tracks", [])):
                        yield await Query.from_base64(track)

    async def _yield_local_tracks(self) -> AsyncIterator[Query]:
        if self.is_album:
            if self.is_local:
                assert isinstance(self._query, LocalFile)
                op = self._query.files_in_tree if self._recursive else self._query.files_in_folder

                async for entry in op():
                    yield entry
        elif self.is_single:
            if self.is_local:
                yield self

    async def _yield_m3u_tracks(self) -> AsyncIterator[Query]:
        if not self.is_m3u or not self.is_album:
            return
        try:
            m3u8 = await m3u_loads(None, uri=f"{self._query}")
            if self._special_local:
                assert isinstance(self._query, LocalFile)
                file = self._query.path
            else:
                file = aiopath.AsyncPath(self._query)
            for track in iter(m3u8.files):
                if is_url(track):
                    yield await Query.from_string(track, dont_search=True)
                else:
                    file_path: aiopath.AsyncPath = aiopath.AsyncPath(track)
                    if await file_path.exists():
                        yield await Query.from_string(file_path, dont_search=True)
                    else:
                        file_path_alt = file.parent / file_path.relative_to(file_path.anchor)
                        if await file_path_alt.exists():
                            yield await Query.from_string(file_path_alt, dont_search=True)
            for playlist in iter(m3u8.playlists):
                if is_url(playlist.uri):
                    yield await Query.from_string(playlist.uri, dont_search=True)
                else:
                    playlist_path: aiopath.AsyncPath = aiopath.AsyncPath(playlist.uri)
                    if await playlist_path.exists():
                        yield await Query.from_string(playlist_path, dont_search=True)
                    else:
                        playlist_path_alt = file.parent / playlist_path.relative_to(playlist_path.anchor)
                        if await playlist_path_alt.exists():
                            yield await Query.from_string(playlist_path_alt, dont_search=True)
        except Exception:
            return

    async def _yield_pls_tracks(self) -> AsyncIterator[Query]:
        if not self.is_pls or not self.is_album:
            return
        if self._special_local:
            assert isinstance(self._query, LocalFile)
            file = self._query.path
        else:
            file = aiopath.AsyncPath(self._query)
        if await file.exists():
            async for entry in self._yield_process_file(file):
                yield entry
        elif is_url(self._query):
            async for entry in self._yield_process_url():
                yield entry

    @staticmethod
    async def _yield_process_file(file):
        async with file.open("r") as f:
            contents = await f.read()
            for line in iter(contents.splitlines()):
                if match := SOURCE_INPUT_MATCH_PLS.match(line):
                    track = match.group("pls_query").strip()
                    if is_url(track):
                        yield await Query.from_string(track, dont_search=True)
                    else:
                        path: aiopath.AsyncPath = aiopath.AsyncPath(track)
                        if await path.exists():
                            yield await Query.from_string(path, dont_search=True)
                        else:
                            path = file.parent / path.relative_to(path.anchor)
                            if await path.exists():
                                yield await Query.from_string(path, dont_search=True)

    async def _yield_process_url(self) -> AsyncIterator[Query]:
        assert not isinstance(self._query, LocalFile)
        async with self.__CLIENT.session.get(self._query) as resp:
            contents = await resp.text()
            for line in iter(contents.splitlines()):
                with contextlib.suppress(Exception):
                    if match := SOURCE_INPUT_MATCH_PLS_TRACK.match(line):
                        yield await Query.from_string(match.group("pls_query").strip(), dont_search=True)

    async def _yield_xspf_tracks(self) -> AsyncIterator[Query]:  # type: ignore
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
            if isinstance(self._query, LocalFile):
                return self._query.parent.stem if await self._query.path.is_file() else self._query.name
            else:
                return self._query
        return None

    async def query_to_queue(self, max_length: int | None = None, name_only: bool = False) -> str:
        return await self.query_to_string(max_length, name_only=name_only)

    @property
    def source(self) -> str:
        return self._source

    @source.setter
    def source(self, source: str) -> None:
        if not self.is_search:
            raise ValueError("Source can only be set for search queries")

        source = source.lower()
        if source not in (allowed := {"ytm", "yt", "sp", "sc", "am", "local", "speak", "tts://", "dz"}):
            raise ValueError(f"Invalid source: {source} - Allowed: {allowed}")
        match source:
            case "ytm":
                source = "YouTube Music"
            case "yt":
                source = "YouTube"
            case "sp":
                source = "Spotify"
            case "sc":
                source = "SoundCloud"
            case "am":
                source = "Apple Music"
            case "local":
                source = "Local"
            case "speak":
                source = "speak"
            case "tts://":
                source = "Google TTS"
            case "dz":
                source = "Deezer"
            case "ym":
                source = "Yandex Music"
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
    async def from_base64(cls, base64_string: str, lazy: bool = False) -> Query:
        data = await cls.__CLIENT.decode_track(base64_string, raise_on_failure=True, lazy=lazy)
        source = data.info.sourceName
        response = await cls.from_string(data.info.uri)
        response._source = cls.__get_source_from_str(source)
        return response

    @classmethod
    def __get_source_from_str(cls, source: str) -> str:
        match source:
            case "spotify":
                return "Spotify"
            case "youtube":
                return "YouTube Music"
            case "soundcloud":
                return "SoundCloud"
            case "deezer":
                return "Deezer"
            case "applemusic":
                return "Apple Music"
            case "local":
                return "Local"
            case "speak":
                return "speak"
            case "gcloud-tts":
                return "Google TTS"
            case "http":
                return "HTTP"
            case "twitch":
                return "Twitch"
            case "vimeo":
                return "Vimeo"
            case "bandcamp":
                return "Bandcamp"
            case "mixcloud":
                return "Mixcloud"
            case "getyarn.io":
                return "GetYarn"
            case "ocremix":
                return "OverClocked ReMix"
            case "reddit":
                return "Reddit"
            case "clypit":
                return "Clyp.it"
            case "pornhub":
                return "PornHub"
            case "soundgasm":
                return "SoundGasm"
            case "tiktok":
                return "TikTok"
            case "niconico":
                return "Niconico"
            case "yandexmusic":
                return "Yandex Music"
            case __:
                return SUPPORTED_SEARCHES[DEFAULT_SEARCH_SOURCE]

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
            return "getyarn.io"
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
        elif self.is_deezer:
            return "deezer"
        elif self.is_yandex_music:
            return "yandexmusic"
        else:
            return "youtube"

    @property
    def source_abbreviation(self) -> str:
        if self.is_spotify:
            return "SP"
        elif self.is_apple_music:
            return "AM"
        elif self.is_youtube:
            return "YT"
        elif self.is_soundcloud:
            return "SC"
        elif self.is_local:
            return "LC"
        elif self.is_twitch:
            return "TW"
        elif self.is_bandcamp:
            return "BC"
        elif self.is_http:
            return "HTTP"
        elif self.is_speak:
            return "TTS"
        elif self.is_gctts:
            return "TTS"
        elif self.is_getyarn:
            return "GY"
        elif self.is_clypit:
            return "CI"
        elif self.is_pornhub:
            return "PH"
        elif self.is_reddit:
            return "RD"
        elif self.is_ocremix:
            return "OCR"
        elif self.is_tiktok:
            return "TT"
        elif self.is_mixcloud:
            return "MX"
        elif self.is_soundgasm:
            return "SG"
        elif self.is_vimeo:
            return "VM"
        elif self.is_deezer:
            return "DZ"
        elif self.is_yandex_music:
            return "YDM"
        else:
            return "YT"


from pylav.players.query.utils import (  # noqa: E305
    process_bandcamp,
    process_deezer,
    process_soundcloud,
    process_spotify,
    process_yandex_music,
    process_youtube,
)
