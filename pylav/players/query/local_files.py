from __future__ import annotations

import os
import pathlib
import sys
import typing
from collections.abc import AsyncIterator

import aiopath  # type: ignore
import asyncstdlib
import discord

try:
    from redbot.core.i18n import Translator  # type: ignore

    _ = Translator("PyLav", pathlib.Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


if typing.TYPE_CHECKING:
    from pylav.players.query.obj import Query


__FULLY_SUPPORTED_MUSIC = (".mp3", ".flac", ".ogg")
__PARTIALLY_SUPPORTED_MUSIC_EXT = (
    ".m3u",
    ".m4a",
    ".aac",
    ".ra",
    ".wav",
    ".opus",
    ".wma",
    ".ts",
    ".au",
    ".m3u8",
    ".pls",
    ".pylav",
    # These do not work
    # ".mid",
    # ".mka",
    # ".amr",
    # ".aiff",
    # ".ac3",
    # ".voc",
    # ".dsf",
)
__PARTIALLY_SUPPORTED_VIDEO_EXT = (
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

__PLUGIN_SUPPORTED_EXT = (
    # https://github.com/esmBot/lava-xm-plugin
    # More can be supported but theres just too many to add,
    #  As people show up with the need to add more I will add them
    #  Full list of supported format: https://github.com/libxmp/libxmp/tree/master/docs/formats
    ".mod",
    ".s3m",
    ".xm",
    ".it",
    ".ahx",
    # -------------------------------
)
__PARTIALLY_SUPPORTED_EXTENSION = (
    __PARTIALLY_SUPPORTED_MUSIC_EXT + __PARTIALLY_SUPPORTED_VIDEO_EXT + __PLUGIN_SUPPORTED_EXT
)

ALL_EXTENSIONS = __FULLY_SUPPORTED_MUSIC + __PARTIALLY_SUPPORTED_EXTENSION

_ROOT_FOLDER: aiopath.AsyncPath | None = None


class LocalFile:
    __slots__ = (
        "_path",
        "_parent",
        "__init",
    )
    _ROOT_FOLDER: aiopath.AsyncPath | None = _ROOT_FOLDER

    def __init__(self, path: str | pathlib.Path | aiopath.AsyncPath):
        if self._ROOT_FOLDER is None:
            # noinspection SpellCheckingInspection
            raise RuntimeError(
                _("Root folder is not initialized, call `{python_function_variable_do_not_translate}`.").format(
                    python_function_variable_do_not_translate="await Client.update_localtracks_folder(folder: str | pathlib.Path)"
                )
            )
        self._path: aiopath.AsyncPath = aiopath.AsyncPath(path)
        self._parent = self._path.parent
        self.__init = False

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self) -> str:
        return f"<LocalFile path={self._path}>"

    async def initialize(self) -> None:
        if self.__init:
            return
        self._path = await discord.utils.maybe_coroutine(self._path.absolute)
        self._path.relative_to(self.root_folder)
        self.__init = True

    @classmethod
    async def add_root_folder(cls, path: str | pathlib.Path | aiopath.AsyncPath, *, create: bool = True) -> None:
        global _ROOT_FOLDER
        _ROOT_FOLDER = cls._ROOT_FOLDER = aiopath.AsyncPath(path)
        if create:
            await _ROOT_FOLDER.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> aiopath.AsyncPath:
        return self._path

    @property
    def sync_path(self) -> pathlib.Path:
        return pathlib.Path(self._path)

    @property
    def root_folder(self) -> aiopath.AsyncPath:
        return self._ROOT_FOLDER

    @property
    def parent(self) -> aiopath.AsyncPath:
        return self._parent

    @property
    def name(self) -> str:
        return typing.cast(str, self._path.name if pathlib.Path(self._path).is_dir() else self._path.stem)

    @property
    def extension(self) -> str:
        return typing.cast(str, self._path.suffix)

    @property
    def initialized(self) -> bool:
        return self.__init

    async def _to_string_user_no_string(
        self,
        path: aiopath.AsyncPath,
        length: int | None = None,
        add_ellipsis: bool = False,
        with_emoji: bool = False,
        no_extension: bool = False,
        is_album: bool = False,
    ) -> str:
        string = typing.cast(str, path.name if await self.path.is_dir() else path.stem if no_extension else path.name)
        if string.startswith("/") or string.startswith("\\"):
            string = string[1:]
        if length is not None:
            string = string[length * -1 :]  # noqa: E203
        if add_ellipsis and length is not None and len(string) > length:
            string = f"\N{HORIZONTAL ELLIPSIS}{string[3:].strip()}"
        if with_emoji:
            emoji = "\N{FILE FOLDER}" if is_album else "\N{MULTIPLE MUSICAL NOTES}"
            string = f"{emoji}{string}"
        return string

    async def to_string_user(
        self,
        length: int | None = None,
        name_only: bool = False,
        add_ellipsis: bool = False,
        with_emoji: bool = False,
        no_extension: bool = False,
        is_album: bool = False,
    ) -> str:
        if with_emoji and length is not None:
            length -= 1
        path = typing.cast(aiopath.AsyncPath, await discord.utils.maybe_coroutine(self.path.absolute))
        is_dir = await self.path.is_dir()
        if name_only:
            string = typing.cast(str, path.name if is_dir else path.stem if no_extension else path.name)
        else:
            root = typing.cast(aiopath.AsyncPath, await discord.utils.maybe_coroutine(self.root_folder.absolute))
            string = str(path).replace(str(root), "")
            if no_extension and not is_dir:
                string = string.removesuffix(path.suffix)
        if not string:
            return await self._to_string_user_no_string(path, length, add_ellipsis, with_emoji, no_extension, is_album)
        if length is not None:
            string = await self._to_string_user_no_length(string, add_ellipsis, length, name_only, no_extension)
        if with_emoji:
            emoji = "\N{FILE FOLDER}" if is_album else "\N{MULTIPLE MUSICAL NOTES}"
            string = f"{emoji}{string}"
        return string

    @staticmethod
    async def _to_string_user_no_length(
        string: str,
        add_ellipsis: bool = False,
        length: int | None = None,
        name_only: bool = False,
        no_extension: bool = False,
    ) -> str:
        temp_path = aiopath.AsyncPath(string)
        parts = list(temp_path.parts)
        parts_reversed = list(parts[::-1])
        if await temp_path.is_file():
            parts_reversed[0] = temp_path.stem if no_extension else temp_path.name
        string_list = parts_reversed[::-1]
        if name_only:
            string = os.path.join(*string_list[-2:])
        else:
            string = os.path.join(*string_list)
        if string.startswith("/") or string.startswith("\\"):
            string = string[1:]
        if length is not None and len(string) > length:
            if not add_ellipsis:
                string = string[length * -1 :]  # noqa: E203
            else:
                string = f"\N{HORIZONTAL ELLIPSIS}{string[length * -1:].strip()}"
        return string

    async def files_in_folder(self, show_folders: bool = False) -> AsyncIterator[Query]:
        parent = self.path if await self.path.is_dir() else self.path.parent
        async for path in self._get_entries_in_folder(parent, show_folders=show_folders):
            yield path

    async def _get_entries_in_folder(
        self, folder: aiopath.AsyncPath, recursive: bool = False, show_folders: bool = False, folder_only: bool = False
    ) -> AsyncIterator[Query]:
        async def _key(path_file: aiopath.AsyncPath) -> str:
            return f"{path_file}"

        from pylav.players.query.obj import Query

        for path in await asyncstdlib.heapq.nsmallest(asyncstdlib.iter(folder.iterdir()), n=sys.maxsize, key=_key):
            if await path.is_dir():
                if recursive:
                    yield await Query.from_string(path)
                    async for p in self._get_entries_in_folder(
                        path, recursive=recursive, show_folders=show_folders, folder_only=folder_only
                    ):
                        yield p
                elif show_folders and path.is_relative_to(self._ROOT_FOLDER):
                    yield await Query.from_string(path)
            elif (not folder_only) and await path.is_file():
                if path.suffix.lower() in ALL_EXTENSIONS and path.is_relative_to(self._ROOT_FOLDER):
                    yield await Query.from_string(path)

    async def files_in_tree(self, show_folders: bool = False) -> AsyncIterator[Query]:
        parent = self.path if await self.path.is_dir() else self.path.parent
        async for path in self._get_entries_in_folder(parent, recursive=True, show_folders=show_folders):
            yield path

    async def folders_in_tree(self) -> AsyncIterator[Query]:
        parent = self.path if await self.path.is_dir() else self.path.parent
        async for path in self._get_entries_in_folder(parent, recursive=True, show_folders=True, folder_only=True):
            yield path
