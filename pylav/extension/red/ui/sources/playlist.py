from __future__ import annotations

import random
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from dacite import from_dict
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_number
from redbot.vendored.discord.ext import menus

from pylav.extension.red.ui.selectors.options.playlist import PlaylistOption
from pylav.logging import getLogger
from pylav.nodes.api.responses.track import Track as LavalinkTrack
from pylav.players.tracks.obj import Track
from pylav.storage.models.playlist import Playlist
from pylav.type_hints.bot import DISCORD_COG_TYPE
from pylav.type_hints.dict_typing import JSON_DICT_TYPE

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

        total_number_of_entries = len(self.entries)
        current_page = humanize_number(page_num + 1)
        total_number_of_pages = humanize_number(self.get_max_pages())

        match total_number_of_entries:
            case 1:
                message = _("Page 1 / 1 | 1 playlist")
            case 0:
                message = _("Page 1 / 1 | 0 playlists")
            case __:
                message = _(
                    "Page {current_page_variable_do_not_translate} / {total_number_of_pages_variable_do_not_translate} | {total_number_of_entries_variable_do_not_translate} playlists"
                ).format(
                    current_page_variable_do_not_translate=current_page,
                    total_number_of_pages_variable_do_not_translate=total_number_of_pages,
                    total_number_of_entries_variable_do_not_translate=humanize_number(total_number_of_entries),
                )

        page.set_footer(text=message)
        return page

    async def get_page(self, page_number):
        if page_number > self.get_max_pages():
            page_number = 0
        base = page_number * self.per_page
        self.select_options.clear()
        self.select_mapping.clear()
        for i, playlist in enumerate(iter(self.entries[base : base + self.per_page]), start=base):  # noqa: E203
            self.select_options.append(await PlaylistOption.from_playlist(playlist=playlist, index=i, bot=self.cog.bot))
            self.select_mapping[f"{playlist.id}"] = playlist
        return self.entries[base : base + self.per_page]  # noqa: E203

    def get_max_pages(self):
        """:class:`int`: The maximum number of pages required to paginate this sequence"""
        return self._max_pages or 1


class TrackMappingSource(menus.ListPageSource):
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

    async def format_page(self, menu: PaginatingMenu, tracks: list[str | JSON_DICT_TYPE]) -> discord.Embed:
        start_index, page_num = self.get_starting_index_and_page_number(menu)
        padding = len(str(start_index + len(tracks)))
        queue_list = ""
        player = self.cog.pylav.get_player(self.guild_id)
        for track_idx, track in enumerate(tracks, start=start_index + 1):
            if isinstance(track, str):
                track = await Track.build_track(
                    node=random.choice(self.cog.pylav.node_manager.nodes),
                    requester=self.author.id,
                    data=track,
                    query=None,
                    player_instance=player,
                )
            else:
                track = await Track.build_track(
                    node=random.choice(self.cog.pylav.node_manager.nodes),
                    requester=self.author.id,
                    data=from_dict(data_class=LavalinkTrack, data=track),
                    query=None,
                    player_instance=player,
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

        total_number_of_entries = len(self.entries)
        current_page = humanize_number(page_num + 1)
        total_number_of_pages = humanize_number(self.get_max_pages())

        match total_number_of_entries:
            case 1:
                message = _("Page 1 / 1 | 1 track")
            case 0:
                message = _("Page 1 / 1 | 0 tracks")
            case __:
                message = _(
                    "Page {current_page_variable_do_not_translate} / {total_number_of_pages_variable_do_not_translate} | {total_number_of_entries_variable_do_not_translate} tracks"
                ).format(
                    current_page_variable_do_not_translate=current_page,
                    total_number_of_pages_variable_do_not_translate=total_number_of_pages,
                    total_number_of_entries_variable_do_not_translate=humanize_number(total_number_of_entries),
                )

        page.set_footer(text=message)
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
        for i, playlist in enumerate(playlists, start=idx_start + 1):
            scope_name = await playlist.get_scope_name(self.cog.bot)
            author_name = await playlist.get_author_name(self.cog.bot) or _("Unknown")
            is_same = scope_name == author_name
            playlist_info = ("\n" + space * 4).join(
                (
                    await playlist.get_name_formatted(with_url=True),
                    _("Identifier: {id_variable_do_not_translate}").format(id_variable_do_not_translate=playlist.id),
                    _("Tracks: {num_variable_do_not_translate}").format(
                        num_variable_do_not_translate=await playlist.size()
                    ),
                    _("Author: {name_variable_do_not_translate}").format(name_variable_do_not_translate=author_name),
                    "\n"
                    if is_same
                    else _("Scope: {scope_variable_do_not_translate}\n").format(
                        scope_variable_do_not_translate=scope_name
                    ),
                )
            )

            plist += f"`{i}.` {playlist_info}"

        embed = await self.cog.pylav.construct_embed(
            messageable=menu.ctx,
            title=_("Playlists you can access in this server:"),
            description=plist,
        )

        total_number_of_entries = len(self.entries)
        current_page = humanize_number(page_num + 1)
        total_number_of_pages = humanize_number(self.get_max_pages())

        match total_number_of_entries:
            case 1:
                message = _("Page 1 / 1 | 1 playlist")
            case 0:
                message = _("Page 1 / 1 | 0 playlists")
            case __:
                message = _(
                    "Page {current_page_variable_do_not_translate} / {total_number_of_pages_variable_do_not_translate} | {total_number_of_entries_variable_do_not_translate} playlists"
                ).format(
                    current_page_variable_do_not_translate=current_page,
                    total_number_of_pages_variable_do_not_translate=total_number_of_pages,
                    total_number_of_entries_variable_do_not_translate=humanize_number(total_number_of_entries),
                )

        embed.set_footer(text=message)
        return embed

    def get_max_pages(self):
        """:class:`int`: The maximum number of pages required to paginate this sequence"""
        return self._max_pages or 1
