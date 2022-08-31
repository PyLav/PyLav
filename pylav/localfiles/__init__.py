from __future__ import annotations

import os
import pathlib
from collections.abc import AsyncIterator
from typing import Final

from discord.utils import maybe_coroutine

from pylav import Query
from pylav.vendored import aiopath

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLavPlayer", pathlib.Path(__file__))
except ImportError:
    _ = lambda x: x

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
    _ROOT_FOLDER: aiopath.AsyncPath | None = _ROOT_FOLDER

    def __init__(self, path: str | pathlib.Path | aiopath.AsyncPath):
        if self._ROOT_FOLDER is None:
            raise RuntimeError(
                _("Root folder not initialized, call Client.update_localtracks_folder(folder: str | pathlib.Path)")
            )
        self._path: aiopath.AsyncPath = aiopath.AsyncPath(path)
        self._parent = self._path.parent
        self.__init = False

    def __str__(self) -> str:
        return str(self._path)

    async def initialize(self) -> None:
        if self.__init:
            return
        self._path = await maybe_coroutine(self._path.absolute)
        self._path.relative_to(self.root_folder)
        self.__init = True

    @classmethod
    async def add_root_folder(cls, path: str | pathlib.Path | aiopath.AsyncPath, *, create: bool = True):
        global _ROOT_FOLDER
        _ROOT_FOLDER = cls._ROOT_FOLDER = aiopath.AsyncPath(path)
        if create:
            await _ROOT_FOLDER.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> aiopath.AsyncPath:
        return self._path

    @property
    def root_folder(self) -> aiopath.AsyncPath:
        return self._ROOT_FOLDER

    @property
    def parent(self) -> aiopath.AsyncPath:
        return self._parent

    @property
    def name(self) -> str:
        return self._path.name if pathlib.Path(self._path).is_dir() else self._path.stem

    @property
    def extension(self) -> str:
        return self._path.suffix

    @property
    def initialized(self) -> bool:
        return self.__init

    async def to_string_user(self, length: int = None, name_only: bool = False, ellipsis: bool = False) -> str:
        path = await maybe_coroutine(self.path.absolute)
        if name_only:
            string = path.name if await self.path.is_dir() else path.stem
        else:
            root = await maybe_coroutine(self.root_folder.absolute)
            string = str(path).replace(str(root), "")
        if not string:
            string = path.name if await self.path.is_dir() else path.stem
            if string.startswith("/") or string.startswith("\\"):
                string = string[1:]
            if length:
                string = string[: length * -1]
            if ellipsis and len(string) + 3 > length:
                string = f"...{string[3:].strip()}"
            return string

        temp_path = aiopath.AsyncPath(string)
        if length is not None:
            parts = list(temp_path.parts)
            parts_reversed = list(parts[::-1])
            if await temp_path.is_file():
                parts_reversed[0] = temp_path.name
            count = 0
            usable_parts = []
            for part in parts_reversed:
                if (not ellipsis) and usable_parts and (count + len(part) + 1) > length:
                    break
                count += len(part) + 1
                usable_parts.append(part)
            string_list = usable_parts[::-1]
            if name_only:
                string = os.path.join(*string_list[-2:])  # Folder and file only
            else:
                string = os.path.join(*string_list)
            if string.startswith("/") or string.startswith("\\"):
                string = string[1:]
            if len(string) > length:
                string = string[length * -1 :]
            if ellipsis and len(string) + 3 > length:
                string = f"...{string[3:].strip()}"
        return string

    async def files_in_folder(self, show_folders: bool = False) -> AsyncIterator[Query]:
        parent = self.path if await self.path.is_dir() else self.path.parent
        async for path in self._get_entries_in_folder(parent, show_folders=show_folders):
            yield path

    async def _get_entries_in_folder(
        self, folder: aiopath.AsyncPath, recursive: bool = False, show_folders: bool = False, folder_only: bool = False
    ) -> AsyncIterator[Query]:
        async for path in folder.iterdir():
            if await path.is_dir():
                if recursive:
                    yield await Query.from_string(path)
                    async for p in self._get_entries_in_folder(
                        path, recursive=recursive, show_folders=show_folders, folder_only=folder_only
                    ):
                        yield p
                elif show_folders and path.is_relative_to(self._ROOT_FOLDER):
                    yield await Query.from_string(path)
            elif not folder_only and await path.is_file():
                if path.suffix.lower() in _ALL_EXTENSIONS and path.is_relative_to(self._ROOT_FOLDER):
                    yield await Query.from_string(path)

    async def files_in_tree(self, show_folders: bool = False) -> AsyncIterator[Query]:
        parent = self.path if await self.path.is_dir() else self.path.parent
        async for path in self._get_entries_in_folder(parent, recursive=True, show_folders=show_folders):
            yield path

    async def folders_in_tree(self) -> AsyncIterator[Query]:
        parent = self.path if await self.path.is_dir() else self.path.parent
        async for path in self._get_entries_in_folder(parent, recursive=True, show_folders=True, folder_only=True):
            yield path
