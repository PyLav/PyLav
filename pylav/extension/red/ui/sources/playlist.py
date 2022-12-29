from __future__ import annotations

import random
from pathlib import Path
from typing import TYPE_CHECKING

import asyncstdlib
import discord
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_number
from redbot.vendored.discord.ext import menus

from pylav.extension.red.ui.selectors.options.playlist import PlaylistOption
from pylav.logging import getLogger
from pylav.players.tracks.obj import Track
from pylav.storage.models.playlist import Playlist
from pylav.type_hints.bot import DISCORD_COG_TYPE
from pylav.utils.vendor.redbot import AsyncIter

if TYPE_CHECKING:
    from pylav.extension.red.ui.menus.generic import PaginatingMenu
    from pylav.extension.red.ui.menus.playlist import PlaylistPickerMenu

LOGGER = getLogger("PyLav.ext.red.ui.sources.playlist")

_ = Translator("PyLav", Path(__file__))
INF = float("inf")
ASCII_ORDER_SORT = "~" * 100


class PlaylistPickerSource(menus.ListPageSource):
    def __init__(self, guild_id: int, cog: DISCORD_COG_TYPE, pages: list[Playlist], message_str: str):
        pages.sort(key=lambda p: p.id)
        super().__init__(entries=pages, per_page=5)
        self.message_str = message_str
        self.per_page = 5
        self.guild_id = guild_id
        self.select_options: list[PlaylistOption] = []
        self.cog = cog
        self.select_mapping: dict[str, Playlist] = {}

    def get_starting_index_and_page_number(self, menu: PlaylistPickerMenu) -> tuple[int, int]:
        page_num = menu.current_page
        start = page_num * self.per_page
        return start, page_num

    async def format_page(self, menu: PlaylistPickerMenu, playlists: list[Playlist]) -> discord.Embed | str:

        idx_start, page_num = self.get_starting_index_and_page_number(menu)
        page = await self.cog.pylav.construct_embed(messageable=menu.ctx, title=self.message_str)
        page.set_footer(
            text=_("Page {page_num}/{total_pages} | {num} playlists").format(
                page_num=humanize_number(page_num + 1),
                total_pages=humanize_number(self.get_max_pages()),
                num=len(self.entries),
            )
        )
        return page

    async def get_page(self, page_number):
        if page_number > self.get_max_pages():
            page_number = 0
        base = page_number * self.per_page
        self.select_options.clear()
        self.select_mapping.clear()
        async for i, playlist in asyncstdlib.enumerate(
            asyncstdlib.iter(self.entries[base : base + self.per_page]), start=base
        ):  # noqa: E203
            self.select_options.append(await PlaylistOption.from_playlist(playlist=playlist, index=i, bot=self.cog.bot))
            self.select_mapping[f"{playlist.id}"] = playlist
        return self.entries[base : base + self.per_page]  # noqa: E203

    def get_max_pages(self):
        """:class:`int`: The maximum number of pages required to paginate this sequence"""
        return self._max_pages or 1


class Base64Source(menus.ListPageSource):
    def __init__(
        self,
        guild_id: int,
        cog: DISCORD_COG_TYPE,
        playlist: Playlist,
        author: discord.abc.User,
        entries: list[str],
        per_page: int = 10,
    ):
        super().__init__(entries=entries, per_page=per_page)
        self.cog = cog
        self.author = author
        self.guild_id = guild_id
        self.playlist = playlist

    def is_paginating(self) -> bool:
        return True

    def get_starting_index_and_page_number(self, menu: PaginatingMenu) -> tuple[int, int]:
        page_num = menu.current_page
        start = page_num * self.per_page
        return start, page_num

    async def format_page(self, menu: PaginatingMenu, tracks: list[str]) -> discord.Embed:
        start_index, page_num = self.get_starting_index_and_page_number(menu)
        padding = len(str(start_index + len(tracks)))
        queue_list = ""
        async for track_idx, track in AsyncIter(tracks).enumerate(start=start_index + 1):
            track = await Track.build_track(
                node=random.choice(self.cog.pylav.node_manager.nodes),
                requester=self.author.id,
                data=track,
                query=None,
            )
            track_description = await track.get_track_display_name(max_length=50, with_url=True)
            diff = padding - len(str(track_idx))
            queue_list += f"`{track_idx}.{' ' * diff}` {track_description}\n"
        page = await self.cog.pylav.construct_embed(
            title="{translation} __{name}__".format(
                name=await self.playlist.fetch_name(), translation=discord.utils.escape_markdown(_("Tracks in"))
            ),
            description=queue_list,
            messageable=menu.ctx,
        )
        text = _("Page {page_num}/{total_pages} | {num_tracks} tracks\n").format(
            page_num=page_num + 1, total_pages=self.get_max_pages(), num_tracks=len(self.entries)
        )
        page.set_footer(text=text)
        return page

    def get_max_pages(self):
        """:class:`int`: The maximum number of pages required to paginate this sequence"""
        return self._max_pages or 1


class PlaylistListSource(menus.ListPageSource):
    def __init__(self, cog: DISCORD_COG_TYPE, pages: list[Playlist]):
        pages.sort(key=lambda p: p.id)
        super().__init__(entries=pages, per_page=5)
        self.cog = cog

    def get_starting_index_and_page_number(self, menu: PaginatingMenu) -> tuple[int, int]:
        page_num = menu.current_page
        start = page_num * self.per_page
        return start, page_num

    async def format_page(self, menu: PaginatingMenu, playlists: list[Playlist]) -> discord.Embed | str:

        idx_start, page_num = self.get_starting_index_and_page_number(menu)
        plist = ""
        space = "\N{EN SPACE}"
        async for i, playlist in AsyncIter(playlists).enumerate(start=idx_start + 1):
            scope_name = await playlist.get_scope_name(self.cog.bot)
            author_name = await playlist.get_author_name(self.cog.bot) or _("Unknown")
            is_same = scope_name == author_name
            playlist_info = ("\n" + space * 4).join(
                (
                    await playlist.get_name_formatted(with_url=True),
                    _("ID: {id}").format(id=playlist.id),
                    _("Tracks: {num}").format(num=await playlist.size()),
                    _("Author: {name}").format(name=author_name),
                    "\n" if is_same else _("Scope: {scope}\n").format(scope=scope_name),
                )
            )

            plist += f"`{i}.` {playlist_info}"

        embed = await self.cog.pylav.construct_embed(
            messageable=menu.ctx,
            title=_("Playlists you can access in this server:"),
            description=plist,
        )
        embed.set_footer(
            text=_("Page {page_num}/{total_pages} | {num} playlists").format(
                page_num=humanize_number(page_num + 1),
                total_pages=humanize_number(self.get_max_pages()),
                num=len(self.entries),
            )
        )
        return embed

    def get_max_pages(self):
        """:class:`int`: The maximum number of pages required to paginate this sequence"""
        return self._max_pages or 1
