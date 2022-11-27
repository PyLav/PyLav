from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import discord
from red_commons.logging import getLogger
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box
from redbot.vendored.discord.ext import menus
from tabulate import tabulate

from pylav.types import CogT
from pylav.utils.theme import EightBitANSI

if TYPE_CHECKING:
    from pylav.red_utils.ui.menus.generic import BaseMenu


LOGGER = getLogger("PyLav.ext.Shared.ui.sources.equalizer")
_ = Translator("PyLavShared", Path(__file__))


class EQPresetsSource(menus.ListPageSource):
    def __init__(self, cog: CogT, pages: list[tuple[str, dict]], per_page: int = 10):
        pages.sort()
        super().__init__(pages, per_page=per_page)
        self.cog = cog

    def get_starting_index_and_page_number(self, menu: BaseMenu) -> tuple[int, int]:
        page_num = menu.current_page
        start = page_num * self.per_page
        return start, page_num

    async def format_page(self, menu: BaseMenu, page: list[tuple[str, dict]]) -> discord.Embed:
        header_name = EightBitANSI.paint_yellow(_("Preset Name"), bold=True, underline=True)
        header_author = EightBitANSI.paint_yellow(_("Author"), bold=True, underline=True)
        data = []
        for preset_name, preset_data in page:
            try:
                author = self.cog.bot.get_user(preset_data["author"])
            except TypeError:
                author = "Build-in"
            data.append(
                {
                    header_name: EightBitANSI.paint_white(preset_name),
                    header_author: EightBitANSI.paint_blue(author),
                }
            )
        return await self.cog.lavalink.construct_embed(
            messageable=menu.ctx, description=box(tabulate(data, headers="keys"), lang="ansi")
        )

    def get_max_pages(self):
        """:class:`int`: The maximum number of pages required to paginate this sequence"""
        return self._max_pages or 1
