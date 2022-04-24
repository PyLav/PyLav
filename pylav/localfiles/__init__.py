from __future__ import annotations

import contextlib
import os
import pathlib
from typing import Final

import aiopath

from pylav import Query

__FULLY_SUPPORTED_MUSIC: Final[tuple[str, ...]] = (".mp3", ".flac", ".ogg")
__PARTIALLY_SUPPORTED_MUSIC_EXT: tuple[str, ...] = (
    ".m3u",
    ".m4a",
    ".aac",
    ".ra",
    ".wav",
    ".opus",
    ".wma",
    ".ts",
    ".au",
    # These do not work
    # ".mid",
    # ".mka",
    # ".amr",
    # ".aiff",
    # ".ac3",
    # ".voc",
    # ".dsf",
)
__PARTIALLY_SUPPORTED_VIDEO_EXT: tuple[str, ...] = (
    ".mp4",
    ".mov",
    ".flv",
    ".webm",
    ".mkv",
    ".wmv",
    ".3gp",
    ".m4v",
    ".mk3d",  # https://github.com/Devoxin/lavaplayer
    ".mka",  # https://github.com/Devoxin/lavaplayer
    ".mks",  # https://github.com/Devoxin/lavaplayer
    # These do not work
    # ".vob",
    # ".mts",
    # ".avi",
    # ".mpg",
    # ".mpeg",
    # ".swf",
)
__PARTIALLY_SUPPORTED_EXTENSION = __PARTIALLY_SUPPORTED_MUSIC_EXT + __PARTIALLY_SUPPORTED_VIDEO_EXT

_ALL_EXTENSIONS = __FULLY_SUPPORTED_MUSIC + __PARTIALLY_SUPPORTED_EXTENSION

_ROOT_FOLDER: aiopath.AsyncPath = None  # type: ignore


class LocalFile:
    __ROOT_FOLDER: aiopath.AsyncPath | None = _ROOT_FOLDER

    def __init__(self, path: str | pathlib.Path | aiopath.AsyncPath):
        if self.__ROOT_FOLDER is None:
            raise RuntimeError(
                "Root folder not initialized, " "call Client.update_localtracks_folder(folder: str | pathlib.Path)"
            )
        self._path: aiopath.AsyncPath = aiopath.AsyncPath(path)
        self._parent = self._path.parent
        self.__init = False

    def __str__(self) -> str:
        return str(self._path)

    async def initialize(self) -> None:
        if self.__init:
            return
        self._path = (await self._path.resolve()).absolute()
        self._path.relative_to(self.root_folder)
        self.__init = True

    @classmethod
    async def add_root_folder(cls, path: str | pathlib.Path | aiopath.AsyncPath, *, create: bool = True):
        global _ROOT_FOLDER
        _ROOT_FOLDER = cls.__ROOT_FOLDER = aiopath.AsyncPath(path)
        if create:
            await _ROOT_FOLDER.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> aiopath.AsyncPath:
        return self._path

    @property
    def root_folder(self) -> aiopath.AsyncPath:
        return self.__ROOT_FOLDER

    @property
    def parent(self) -> aiopath.AsyncPath:
        return self._parent

    @property
    def name(self) -> str:
        return self._path.name

    @property
    def extension(self) -> str:
        return self._path.suffix

    @property
    def initialized(self) -> bool:
        return self.__init

    async def to_string_user(self, length: int = None, name_only: bool = False) -> str:
        path = self.path.absolute()
        if name_only:
            string = path.name
        else:
            root = self.root_folder.absolute()
            string = str(path).replace(str(root), "")
        if string.startswith(os.sep):
            string = string[1:]
        if not string:
            return self.path.name
        chunked = False
        if length is not None:
            while len(string) > length - 4 and os.sep in string:
                string = string.split(os.sep, 1)[-1]
                chunked = True
        if chunked:
            string = f"...{os.sep}{string}"
        return string

    async def files_in_folder(self) -> list[Query]:
        if not await self.path.is_dir():
            parent = self.path.parent
        else:
            parent = self.path
        files = []
        async for path in parent.glob(*_ALL_EXTENSIONS):
            with contextlib.suppress(ValueError):
                if path.relative_to(parent):
                    files.append(await Query.from_string(path))
        return sorted(files, key=lambda x: str(x).lower())

    async def files_in_tree(self) -> list[Query]:
        if not await self.path.is_dir():
            parent = self.path.parent
        else:
            parent = self.path

        files = []
        async for path in parent.rglob(*_ALL_EXTENSIONS):
            with contextlib.suppress(ValueError):
                if path.relative_to(parent):
                    files.append(await Query.from_string(path))
        return sorted(files, key=lambda x: str(x).lower())
