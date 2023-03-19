from __future__ import annotations

import asyncio
import hashlib
import pathlib
from typing import TYPE_CHECKING

import aiopath
from watchfiles import Change, awatch

from pylav.logging import getLogger
from pylav.nodes.api.responses import rest_api
from pylav.nodes.api.responses.track import Track
from pylav.players.query.local_files import ALL_EXTENSIONS
from pylav.players.query.obj import Query

if TYPE_CHECKING:
    from pylav.core.client import Client

LOGGER = getLogger("PyLav.LocalTrackCache")


class LocalTrackCache:
    __slots__ = (
        "__pylav",
        "__ready",
        "__monitor",
        "__shutdown",
        "__query_cache",
        "__track_cache",
        "__root_folder",
        "__query_lock",
        "__track_lock",
        "__path_to_query_cache",
    )

    def __init__(self, client: Client, root: str | pathlib.Path | aiopath.Path) -> None:
        self.__shutdown = False
        self.__pylav = client
        self.__query_cache: dict[str, Query] = {}
        self.__track_cache: dict[str, Track] = {}
        self.__path_to_query_cache: dict[str, Query] = {}
        self.__query_lock = asyncio.Lock()
        self.__track_lock = asyncio.Lock()
        self.__root_folder = pathlib.Path(root)
        self.__ready = asyncio.Event()
        self.__monitor = asyncio.create_task(self.file_watcher())

    def __bool__(self) -> bool:
        return not self.__shutdown

    @property
    def hexdigest_to_query(self) -> dict[str, Query]:
        return self.__query_cache

    @property
    def path_to_query(self) -> dict[str, Query]:
        return self.__path_to_query_cache

    @property
    def path_to_track(self) -> dict[str, Track]:
        return self.__track_cache

    @property
    def root_folder(self) -> pathlib.Path:
        return self.__root_folder

    @property
    def is_ready(self) -> bool:
        return self.__ready.is_set()

    async def initialize(self):
        await self.__pylav.wait_until_ready()
        await self.update()
        self.__ready.set()

    async def shutdown(self):
        self.__shutdown = True
        self.__monitor.cancel()
        self.__ready.clear()
        await self.wipe_cache()

    async def _add_to_query_cache(self, query: Query, path: str) -> None:
        if self.__shutdown:
            return
        async with self.__query_lock:
            self.__query_cache[hashlib.md5(f"{query._query}".encode()).hexdigest()] = query
            self.__path_to_query_cache[path] = query

    async def _remove_from_query_cache(self, query: Query, path: str) -> None:
        if self.__shutdown:
            return
        async with self.__query_lock:
            self.__query_cache.pop(hashlib.md5(f"{query._query}".encode()).hexdigest(), None)
            self.__path_to_query_cache.pop(path, None)

    async def _add_to_track_cache(self, track: Track, path: pathlib.Path) -> None:
        if self.__shutdown:
            return
        async with self.__track_lock:
            self.__track_cache[f"{path}"] = track

    async def _remove_from_track_cache(self, path: pathlib.Path) -> None:
        if self.__shutdown:
            return
        async with self.__track_lock:
            self.__track_cache.pop(f"{path}", None)

    async def wipe_cache(self) -> None:
        await self.__track_lock.acquire()
        await self.__query_lock.acquire()
        self.__track_cache.clear()
        self.__query_cache.clear()
        self.__path_to_query_cache.clear()
        self.__track_lock.release()
        self.__query_lock.release()

    async def file_watcher(self):
        await self.__ready.wait()
        async for changes in awatch(self.root_folder, recursive=True):
            if self.__shutdown:
                return
            await self._process_changes(changes)

    async def _process_changes(self, changes: set[tuple[Change, str]]) -> None:
        for change, path in changes:
            path_obj = pathlib.Path(path)
            if (not path_obj.is_dir()) and path_obj.suffix.lower() not in ALL_EXTENSIONS:
                continue
            if change == Change.added:
                await self._process_added(path, path_obj)
                LOGGER.verbose(f"Added {path}")
            elif change == Change.modified:
                await self._process_modified(path, path_obj, modified=True)
                LOGGER.verbose(f"Modified {path}")
            elif change == Change.deleted:
                await self._process_deleted(path, path_obj)
                LOGGER.verbose(f"Deleted {path}")

    async def _process_added(self, path: str, path_obj: pathlib.Path, modified: bool = False) -> None:
        if self.__shutdown:
            return
        query = await Query.from_string(path_obj)
        if path_obj.is_dir():
            await self._add_to_query_cache(query, path)
            return
        await asyncio.sleep(0.1)
        track = await self.__pylav.get_tracks(query, bypass_cache=modified)
        if isinstance(track, (rest_api.TrackResponse, rest_api.SearchResponse, rest_api.PlaylistResponse)):
            await self._add_to_query_cache(query, path)
            if isinstance(track, rest_api.TrackResponse):
                await self._add_to_track_cache(track.data, path)
            elif isinstance(track, rest_api.PlaylistResponse):
                await self._add_to_track_cache(track.data.tracks, path)
            else:
                await self._add_to_track_cache(track.data[0], path)

    async def _process_modified(self, path: str, path_obj: pathlib.Path, modified: bool = True) -> None:
        if self.__shutdown:
            return
        query = await Query.from_string(path_obj)
        await self._remove_from_query_cache(query, path)
        await self._remove_from_track_cache(path)
        if path_obj.is_dir():
            await self._add_to_query_cache(query, path)
            return
        await asyncio.sleep(0.1)
        track = await self.__pylav.search_query(query, bypass_cache=modified)
        if isinstance(track, (rest_api.TrackResponse, rest_api.SearchResponse, rest_api.PlaylistResponse)):
            await self._add_to_query_cache(query, path)
            if isinstance(track, rest_api.TrackResponse):
                await self._add_to_track_cache(track.data, path)
            elif isinstance(track, rest_api.PlaylistResponse):
                await self._add_to_track_cache(track.data.tracks, path)
            else:
                await self._add_to_track_cache(track.data[0], path)

    async def _process_deleted(self, path: str, path_obj: pathlib.Path) -> None:
        if self.__shutdown:
            return
        query = await Query.from_string(path_obj)
        await self._remove_from_query_cache(query, path)
        await self._remove_from_track_cache(path)

    async def update(self) -> None:
        if self.__shutdown:
            return
        await self.__pylav.wait_until_ready()
        LOGGER.debug("Updating cache")
        for entry in self.__root_folder.rglob("*"):
            if (not entry.is_dir()) and entry.suffix.lower() not in ALL_EXTENSIONS:
                continue
            await self._process_added(f"{entry}", entry)
        LOGGER.debug("Finished updating cache")
