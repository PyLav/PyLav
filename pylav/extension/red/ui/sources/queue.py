from __future__ import annotations

from collections.abc import Iterable
from itertools import islice
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from redbot.core.i18n import Translator
from redbot.vendored.discord.ext import menus

from pylav.extension.red.ui.selectors.options.queue import QueueTrackOption, SearchTrackOption
from pylav.logging import getLogger
from pylav.players.tracks.obj import Track
from pylav.type_hints.bot import DISCORD_COG_TYPE

if TYPE_CHECKING:
    from pylav.extension.red.ui.menus.queue import QueueMenu, QueuePickerMenu

LOGGER = getLogger("PyLav.ext.red.ui.sources.queue")

_ = Translator("PyLav", Path(__file__))


class SearchPickerSource(menus.ListPageSource):
    entries: list[Track]

    def __init__(self, entries: list[Track], cog: DISCORD_COG_TYPE, per_page: int = 10):
        super().__init__(entries=entries, per_page=per_page)
        self.per_page = 25
        self.select_options: list[SearchTrackOption] = []
        self.cog = cog
        self.select_mapping: dict[str, Track] = {}

    async def get_page(self, page_number):
        if page_number > self.get_max_pages():
            page_number = 0
        base = page_number * self.per_page
        self.select_options.clear()
        self.select_mapping.clear()
        for i, track in enumerate(iter(self.entries[base : base + self.per_page]), start=base):  # noqa: E203
            self.select_options.append(await SearchTrackOption.from_track(track=track, index=i))
            self.select_mapping[track.id] = track
        return []

    async def format_page(self, menu: QueueMenu, entries: list[Track]) -> str:
        return ""

    def get_max_pages(self):
        """:class:`int`: The maximum number of pages required to paginate this sequence"""
        return self._max_pages or 1


class QueueSource(menus.ListPageSource):
    def __init__(self, guild_id: int, cog: DISCORD_COG_TYPE, history: bool = False):  # noqa
        self.cog = cog
        self.current_player = None
        self.per_page = 10
        self.guild_id = guild_id
        self.history = history

    @property
    def entries(self) -> Iterable[Track]:
        if player := self.cog.pylav.get_player(self.guild_id):
            return player.history.raw_queue if self.history else player.queue.raw_queue
        else:
            return []

    def is_paginating(self) -> bool:
        return True

    async def get_page(self, page_number: int) -> list[Track]:
        base = page_number * self.per_page
        return list(islice(self.entries, base, base + self.per_page))

    def get_max_pages(self) -> int:
        player = self.cog.pylav.get_player(self.guild_id)
        if not player:
            return 1
        pages, left_over = divmod(player.history.size() if self.history else player.queue.size(), self.per_page)

        if left_over:
            pages += 1
        return pages or 1

    def get_starting_index_and_page_number(self, menu: QueueMenu) -> tuple[int, int]:
        page_num = menu.current_page
        start = page_num * self.per_page
        return start, page_num

    async def format_page(self, menu: QueueMenu, tracks: list[Track]) -> dict[str, discord.Embed | str | discord.File]:
        if not (player := self.cog.pylav.get_player(menu.ctx.guild.id)):
            return {
                "embed": await self.cog.pylav.construct_embed(
                    description=_("I am not connected to any voice channel at the moment."), messageable=menu.ctx
                )
            }
        self.current_player = player
        return (
            await player.get_queue_page(
                page_index=menu.current_page,
                per_page=self.per_page,
                total_pages=self.get_max_pages(),
                embed=True,
                messageable=menu.ctx,
                history=self.history,
            )
            if player.current and (player.history.size() if self.history else True)
            else {
                "embed": await self.cog.pylav.construct_embed(
                    description=_("I am not currently playing anything on this server.")
                    if self.history
                    else _("I am not currently playing anything on this server."),
                    messageable=menu.ctx,
                )
            }
        )


class QueuePickerSource(QueueSource):
    def __init__(self, guild_id: int, cog: DISCORD_COG_TYPE):
        super().__init__(guild_id, cog=cog)
        self.per_page = 25
        self.select_options: list[QueueTrackOption] = []
        self.select_mapping: dict[str, Track] = {}
        self.cog = cog

    async def get_page(self, page_number):
        if page_number > self.get_max_pages():
            page_number = 0
        base = page_number * self.per_page
        self.select_options.clear()
        self.select_mapping.clear()
        for i, track in enumerate(islice(self.entries, base, base + self.per_page), start=base):
            self.select_options.append(await QueueTrackOption.from_track(track=track, index=i))
            self.select_mapping[track.id] = track
        return []

    async def format_page(
        self, menu: QueuePickerMenu, tracks: list[Track]
    ) -> dict[str, discord.Embed | str | discord.File]:
        if not (player := self.cog.pylav.get_player(menu.ctx.guild.id)):
            return {
                "embed": await self.cog.pylav.construct_embed(
                    description=_("I am not connected to any voice channel at the moment."), messageable=menu.ctx
                )
            }
        self.current_player = player
        return (
            await player.get_queue_page(
                page_index=menu.current_page,
                per_page=self.per_page,
                total_pages=self.get_max_pages(),
                embed=True,
                messageable=menu.ctx,
            )
            if player.current
            else {
                "embed": await self.cog.pylav.construct_embed(
                    description=_("I am not currently playing anything on this server."),
                    messageable=menu.ctx,
                )
            }
        )
