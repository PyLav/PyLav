from __future__ import annotations

import asyncio
import hashlib
import pathlib
from typing import TYPE_CHECKING

import aiopath
from discord.utils import utcnow
from expiringdict import ExpiringDict
from watchfiles import Change, awatch

from pylav.constants.config import POSTGRES_CONNECTIONS
from pylav.logging import getLogger
from pylav.nodes.api.responses.track import Track
from pylav.players.query.local_files import ALL_EXTENSIONS
from pylav.players.query.obj import Query

if TYPE_CHECKING:
    from pylav.core.client import Client

LOGGER = getLogger("PyLav.LocalTrackCache")


class LocalTrackCache:
    """A cache for local tracks."""

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
        "__counter",
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
        self.__counter = ExpiringDict(max_len=float("inf"), max_age_seconds=5)

    def __bool__(self) -> bool:
        return not self.__shutdown

    @property
    def hexdigest_to_query(self) -> dict[str, Query]:
        """The hexdigest to query cache."""
        return self.__query_cache

    @property
    def path_to_query(self) -> dict[str, Query]:
        """The path to query cache."""
        return self.__path_to_query_cache

    @property
    def path_to_track(self) -> dict[str, Track]:
        """The path to track cache."""
        return self.__track_cache

    @property
    def root_folder(self) -> pathlib.Path:
        """The root folder of the local track cache."""
        return self.__root_folder

    @property
    def is_ready(self) -> bool:
        """Whether the local track cache is ready."""
        return self.__ready.is_set()

    async def initialize(self):
        """Initialize the local track cache."""
        await self.__pylav.wait_until_ready()
        await self.update()
        self.__ready.set()

    async def shutdown(self):
        """Shutdown the local track cache."""
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
        """Wipe the local track cache."""
        await self.__track_lock.acquire()
        await self.__query_lock.acquire()
        self.__track_cache.clear()
        self.__query_cache.clear()
        self.__path_to_query_cache.clear()
        self.__track_lock.release()
        self.__query_lock.release()

    async def file_watcher(self):
        """A file watcher for the local track cache."""
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
            match change:
                case Change.added:
                    await self._process_added(path, path_obj)
                    LOGGER.trace(f"Added {path}")
                case Change.modified:
                    await self._process_modified(path, path_obj, modified=True)
                    LOGGER.trace(f"Modified {path}")
                case Change.deleted:
                    await self._process_deleted(path, path_obj)
                    LOGGER.trace(f"Deleted {path}")

    async def _process_added(self, path: str, path_obj: pathlib.Path, modified: bool = False) -> None:
        if self.__shutdown:
            return
        query = await Query.from_string(path_obj)
        if path_obj.is_dir():
            await self._add_to_query_cache(query, path)
            return
        self.__counter["added"] = self.__counter.get("added", default=0) + 1
        if self.__counter["added"] % 3 == 10:
            self.__counter["added"] = 0
            should_sleep = True
        else:
            should_sleep = False
        track = await self.__pylav.search_query(query, bypass_cache=modified, sleep=should_sleep)
        if track.loadType in {"track", "playlist", "search"}:
            await self._add_to_query_cache(query, path)
            match track.loadType:
                case "track":
                    await self._add_to_track_cache(track.data, path_obj)
                case "playlist":
                    for track in track.data.tracks:
                        await self._add_to_track_cache(track, path_obj)
                case "search":
                    for track in track.data:
                        await self._add_to_track_cache(track, path_obj)

    async def _process_modified(self, path: str, path_obj: pathlib.Path, modified: bool = True) -> None:
        if self.__shutdown:
            return
        query = await Query.from_string(path_obj)
        await self._remove_from_query_cache(query, path)
        await self._remove_from_track_cache(path_obj)
        if path_obj.is_dir():
            await self._add_to_query_cache(query, path)
            return
        track = await self.__pylav.search_query(query, bypass_cache=modified, sleep=True)
        if track.loadType in {"track", "playlist", "search"}:
            await self._add_to_query_cache(query, path)
            match track.loadType:
                case "track":
                    await self._add_to_track_cache(track.data, path_obj)
                case "playlist":
                    for track in track.data.tracks:
                        await self._add_to_track_cache(track, path_obj)
                case "search":
                    for track in track.data:
                        await self._add_to_track_cache(track, path_obj)

    async def _process_deleted(self, path: str, path_obj: pathlib.Path) -> None:
        if self.__shutdown:
            return
        query = await Query.from_string(path_obj)
        await self._remove_from_query_cache(query, path)
        await self._remove_from_track_cache(path_obj)

    async def update(self) -> None:
        """Update the local track cache."""
        if self.__shutdown:
            return
        await self.__pylav.wait_until_ready()
        chunk_size = min(POSTGRES_CONNECTIONS, 50)
        LOGGER.debug("Updating cache")
        start = utcnow()
        chunk = []
        for entry in self.__root_folder.rglob("*"):
            if (not entry.is_dir()) and entry.suffix.lower() not in ALL_EXTENSIONS:
                continue
            chunk.append(entry)
            if len(chunk) == chunk_size:
                await asyncio.gather(*[self._process_added(f"{entry}", entry) for entry in chunk])
                chunk = []
        if chunk:
            await asyncio.gather(*[self._process_added(f"{entry}", entry) for entry in chunk])

        LOGGER.debug("Finished updating cache in %s", utcnow() - start)
