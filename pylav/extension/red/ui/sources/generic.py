from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box, humanize_number
from redbot.vendored.discord.ext import menus

from pylav.extension.red.ui.selectors.options.generic import EntryOption
from pylav.extension.red.utils import Mutator
from pylav.helpers.format.ascii import EightBitANSI
from pylav.logging import getLogger
from pylav.type_hints.bot import DISCORD_COG_TYPE
from pylav.type_hints.generics import ANY_GENERIC_TYPE

if TYPE_CHECKING:
    from pylav.extension.red.ui.menus.generic import BaseMenu, EntryPickerMenu

LOGGER = getLogger("PyLav.ext.red.ui.sources.generic")

_ = Translator("PyLav", Path(__file__))


class PreformattedSource(menus.ListPageSource):
    def __init__(self, pages: Iterable[str | discord.Embed]):
        super().__init__(pages, per_page=1)

    async def format_page(self, menu: BaseMenu, page: str | discord.Embed) -> discord.Embed | str:
        return page

    def get_max_pages(self):
        """:class:`int`: The maximum number of pages required to paginate this sequence"""
        return self._max_pages or 1


class ListSource(menus.ListPageSource):
    def __init__(self, cog: DISCORD_COG_TYPE, title: str, pages: list[str], per_page: int = 10):
        pages.sort()
        super().__init__(pages, per_page=per_page)
        self.title = title
        self.cog = cog

    def get_starting_index_and_page_number(self, menu: BaseMenu) -> tuple[int, int]:
        page_num = menu.current_page
        start = page_num * self.per_page
        return start, page_num

    async def format_page(self, menu: BaseMenu, page: list[str]) -> discord.Embed:
        idx_start, page_num = self.get_starting_index_and_page_number(menu)
        text = "".join(
            f"{EightBitANSI.paint_white(i)}. {EightBitANSI.paint_blue(entry)}"
            for i, entry in enumerate(page, idx_start + 1)
        )

        output = box(text, lang="ansi")
        return await self.cog.pylav.construct_embed(messageable=menu.ctx, title=self.title, description=output)

    def get_max_pages(self):
        """:class:`int`: The maximum number of pages required to paginate this sequence"""
        return self._max_pages or 1


class EntryPickerSource(menus.ListPageSource):
    def __init__(
        self, guild_id: int, cog: DISCORD_COG_TYPE, pages: list[ANY_GENERIC_TYPE], message_str: str, per_page: int = 25
    ):
        super().__init__(entries=pages, per_page=per_page)
        self.message_str = message_str
        self.guild_id = guild_id
        self.select_options: list[EntryOption] = []
        self.cog = cog
        self.select_mapping: dict[str, ANY_GENERIC_TYPE] = {}

    def get_starting_index_and_page_number(self, menu: EntryPickerMenu) -> tuple[int, int]:
        page_num = menu.current_page
        start = page_num * self.per_page
        return start, page_num

    async def format_page(self, menu: EntryPickerMenu, entry: list[ANY_GENERIC_TYPE]) -> discord.Embed | str:
        idx_start, page_num = self.get_starting_index_and_page_number(menu)
        page = await self.cog.pylav.construct_embed(messageable=menu.ctx, title=self.message_str)

        total_number_of_entries = len(self.entries)
        current_page = humanize_number(page_num + 1)
        total_number_of_pages = humanize_number(self.get_max_pages())

        match total_number_of_entries:
            case 1:
                message = _("Page 1 / 1 | 1 entry")
            case 0:
                message = _("Page 1 / 1 | 0 entries")
            case __:
                message = _(
                    "Page {current_page_variable_do_not_translate} / {total_number_of_pages_variable_do_not_translate} | {total_number_of_entries_variable_do_not_translate} entries"
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
        for i, entry in enumerate(iter(self.entries[base : base + self.per_page]), start=base):  # n
            new_entry = Mutator(entry)
            self.select_options.append(await EntryOption.from_entry(entry=new_entry, index=i))
            self.select_mapping[f"{new_entry.id}"] = entry
        return self.entries[base : base + self.per_page]  # noqa: E203

    def get_max_pages(self):
        """:class:`int`: The maximum number of pages required to paginate this sequence"""
        return self._max_pages or 1
