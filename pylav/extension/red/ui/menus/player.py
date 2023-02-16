from __future__ import annotations

from pathlib import Path
from typing import Any

import discord
from redbot.core.i18n import Translator

from pylav.core.context import PyLavContext
from pylav.extension.red.ui.buttons.generic import CloseButton, LabelButton, NavigateButton, RefreshButton
from pylav.extension.red.ui.buttons.player import DisconnectAllButton, DisconnectButton, StopTrackButton
from pylav.extension.red.ui.menus.generic import BaseMenu
from pylav.extension.red.ui.sources.player import PlayersSource
from pylav.helpers.format.strings import shorten_string
from pylav.type_hints.bot import DISCORD_BOT_TYPE, DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

_ = Translator("PyLav", Path(__file__))


class StatsMenu(BaseMenu):
    _source: PlayersSource

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        bot: DISCORD_BOT_TYPE,
        source: PlayersSource,
        original_author: discord.abc.User,
        *,
        clear_buttons_after: bool = False,
        delete_after_timeout: bool = True,
        timeout: int = 600,
        message: discord.Message = None,
        starting_page: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            cog=cog,
            bot=bot,
            source=source,
            clear_buttons_after=clear_buttons_after,
            delete_after_timeout=delete_after_timeout,
            timeout=timeout,
            message=message,
            starting_page=starting_page,
            **kwargs,
        )

        self.forward_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=1,
            row=0,
            cog=cog,
        )
        self.backward_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=-1,
            row=0,
            cog=cog,
        )
        self.first_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}",
            direction=0,
            row=0,
            cog=cog,
        )
        self.last_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}",
            direction=self.source.get_max_pages,
            row=0,
            cog=cog,
        )
        self.refresh_button = RefreshButton(
            style=discord.ButtonStyle.grey,
            row=0,
            cog=cog,
        )

        self.close_button = CloseButton(
            style=discord.ButtonStyle.red,
            row=1,
            cog=cog,
        )
        self.stop_button = StopTrackButton(
            style=discord.ButtonStyle.red,
            row=1,
            cog=cog,
        )
        self.queue_disconnect_label = LabelButton(
            disconnect_type_translation=shorten_string(max_length=100, string=_("selected")),
            row=2,
            multiple=False,
        )
        self.queue_disconnect = DisconnectButton(
            style=discord.ButtonStyle.red,
            row=2,
            cog=cog,
        )
        self.queue_disconnect_inactive_label = LabelButton(
            disconnect_type_translation=shorten_string(max_length=100, string=_("inactive")),
            row=3,
        )
        self.queue_disconnect_inactive = DisconnectAllButton(
            disconnect_type="inactive",
            style=discord.ButtonStyle.red,
            row=3,
            cog=cog,
        )
        self.queue_disconnect_all_label = LabelButton(
            disconnect_type_translation=shorten_string(max_length=100, string=_("all")),
            row=4,
        )
        self.queue_disconnect_all = DisconnectAllButton(
            disconnect_type="all",
            style=discord.ButtonStyle.red,
            row=4,
            cog=cog,
        )
        self.author = original_author

    async def prepare(self):
        self.clear_items()
        max_pages = self.source.get_max_pages()
        self.add_item(self.close_button)
        self.add_item(self.stop_button)
        self.add_item(self.queue_disconnect_label)
        self.add_item(self.queue_disconnect)
        self.add_item(self.first_button)
        self.add_item(self.backward_button)
        self.add_item(self.forward_button)
        self.add_item(self.last_button)
        self.add_item(self.refresh_button)
        if self.source.specified_guild is None or not (self.cog.pylav.player_manager.get(self.source.specified_guild)):
            self.add_item(self.queue_disconnect_inactive_label)
            self.add_item(self.queue_disconnect_inactive)
            self.add_item(self.queue_disconnect_all_label)
            self.add_item(self.queue_disconnect_all)

        self.forward_button.disabled = False
        self.backward_button.disabled = False
        self.first_button.disabled = False
        self.last_button.disabled = False
        self.refresh_button.disabled = False
        self.queue_disconnect.disabled = False
        self.queue_disconnect_all.disabled = False
        self.queue_disconnect_inactive.disabled = False
        self.stop_button.disabled = False
        self.queue_disconnect_label.disabled = True
        self.queue_disconnect_all_label.disabled = True
        self.queue_disconnect_inactive_label.disabled = True

        if max_pages > 2:
            self.forward_button.disabled = False
            self.backward_button.disabled = False
            self.first_button.disabled = False
            self.last_button.disabled = False
        elif max_pages == 2:
            self.forward_button.disabled = False
            self.backward_button.disabled = False
            self.first_button.disabled = True
            self.last_button.disabled = True
        elif max_pages == 1:
            self.forward_button.disabled = True
            self.backward_button.disabled = True
            self.first_button.disabled = True
            self.last_button.disabled = True
        player = self.source.current_player
        if not player:
            self.stop_button.disabled = True
            self.queue_disconnect.disabled = True
            self.queue_disconnect_label.disabled = True
            self.queue_disconnect_inactive_label.disabled = True
            self.queue_disconnect_all_label.disabled = True
        elif not player.current:
            self.stop_button.disabled = True

        if len(self.source.entries) <= 1:
            self.queue_disconnect_inactive.disabled = True
            self.queue_disconnect_all.disabled = True

        if not [p for p in iter(self.cog.pylav.player_manager.connected_players) if not p.is_active]:
            self.queue_disconnect_inactive.disabled = True

    @property
    def source(self) -> PlayersSource:
        return self._source

    async def start(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE):
        if isinstance(ctx, discord.Interaction):
            ctx = await self.cog.bot.get_context(ctx)
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer(ephemeral=True)
        self.ctx = ctx
        await self.send_initial_message(ctx)

    async def get_page(self, page_num: int):
        if len(self.source.entries) == 0:
            self._source.current_player = None
            return {
                "content": None,
                "embed": await self.cog.pylav.construct_embed(
                    messageable=self.ctx,
                    title=shorten_string(max_length=100, string=_("I am not in any voice channel currently.")),
                ),
            }
        try:
            if page_num >= self._source.get_max_pages():
                page_num = 0
                self.current_page = 0
            page = await self.source.get_page(page_num)
        except IndexError:
            self.current_page = 0
            page = await self.source.get_page(self.current_page)
        value = await self.source.format_page(self, page)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {"content": value, "embed": None}
        elif isinstance(value, discord.Embed):
            return {"embed": value, "content": None}
