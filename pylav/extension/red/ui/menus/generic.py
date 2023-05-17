from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Any

import discord
from redbot.core.i18n import Translator
from redbot.vendored.discord.ext import menus

from pylav.core.context import PyLavContext
from pylav.extension.red.ui.buttons.generic import CloseButton, NavigateButton, NoButton, RefreshButton, YesButton
from pylav.extension.red.ui.selectors.generic import EntrySelectSelector
from pylav.extension.red.ui.sources.generic import EntryPickerSource
from pylav.helpers.format.strings import shorten_string
from pylav.logging import getLogger
from pylav.type_hints.bot import DISCORD_BOT_TYPE, DISCORD_COG_TYPE, DISCORD_CONTEXT_TYPE, DISCORD_INTERACTION_TYPE

LOGGER = getLogger("PyLav.ext.red.ui.menu.generic")
_ = Translator("PyLav", Path(__file__))


class BaseMenu(discord.ui.View):
    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        bot: DISCORD_BOT_TYPE,
        source: menus.ListPageSource,
        *,
        delete_after_timeout: bool = True,
        timeout: int = 120,
        message: discord.Message = None,
        starting_page: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            timeout=timeout,
        )
        self.author = None
        self.ctx = None
        self.cog = cog
        self.bot = bot
        self.message = message
        self._source = source
        self.delete_after_timeout = delete_after_timeout
        self.current_page = starting_page or kwargs.get("page_start", 0)
        self._running = True

    @property
    def source(self) -> menus.ListPageSource:
        return self._source

    async def on_timeout(self):
        self._running = False
        if self.message is None:
            return
        with contextlib.suppress(discord.HTTPException):
            if self.delete_after_timeout and not self.message.flags.ephemeral:
                await self.message.delete()
            else:
                await self.message.edit(view=None)

    async def get_page(self, page_num: int):
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

    async def send_initial_message(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE):
        self.ctx = ctx
        kwargs = await self.get_page(self.current_page)
        await self.prepare()
        self.message = await ctx.send(view=self, ephemeral=True, **kwargs)
        return self.message

    async def show_page(self, page_number, interaction: DISCORD_INTERACTION_TYPE):
        self.current_page = page_number
        kwargs = await self.get_page(self.current_page)
        await self.prepare()
        attachments = []
        if "file" in kwargs:
            attachments = [kwargs.pop("file")]
        elif "files" in kwargs:
            attachments = kwargs.pop("files")
        if attachments:
            kwargs["attachments"] = attachments
        if self.message is not None:
            if not interaction.response.is_done():
                await interaction.response.pong()
            await self.message.edit(view=self, **kwargs)
        elif not interaction.response.is_done():
            await interaction.response.edit_message(view=self, **kwargs)

    async def show_checked_page(self, page_number: int, interaction: DISCORD_INTERACTION_TYPE) -> None:
        max_pages = self._source.get_max_pages()
        with contextlib.suppress(IndexError):
            if max_pages is None or max_pages > page_number >= 0:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(page_number, interaction)
            elif page_number >= max_pages:
                await self.show_page(0, interaction)
            else:
                await self.show_page(max_pages - 1, interaction)

    async def interaction_check(self, interaction: DISCORD_INTERACTION_TYPE):
        """Just extends the default reaction_check to use owner_ids"""
        if (not await self.bot.allowed_by_whitelist_blacklist(interaction.user, guild=interaction.guild)) or (
            self.author and (interaction.user.id != self.author.id)
        ):
            await interaction.response.send_message(
                content=_("You are not authorized to interact with this."), ephemeral=True
            )
            return False
        return True

    async def prepare(self):
        return

    async def on_error(
        self, error: Exception, item: discord.ui.Item[Any], interaction: DISCORD_INTERACTION_TYPE
    ) -> None:
        LOGGER.info("Ignoring exception in view %s for item %s:", self, item, exc_info=error)


class PaginatingMenu(BaseMenu):
    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        bot: DISCORD_BOT_TYPE,
        source: Any,
        original_author: discord.abc.User,
        *,
        clear_buttons_after: bool = True,
        delete_after_timeout: bool = False,
        timeout: int = 120,
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
        self.author = original_author
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
            row=0,
            cog=cog,
        )
        self.add_item(self.close_button)
        self.add_item(self.first_button)
        self.add_item(self.backward_button)
        self.add_item(self.forward_button)
        self.add_item(self.last_button)

    async def start(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE):
        if isinstance(ctx, discord.Interaction):
            ctx = await self.cog.bot.get_context(ctx)
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer(ephemeral=True)
        self.ctx = ctx
        await self.send_initial_message(ctx)

    async def prepare(self):
        max_pages = self.source.get_max_pages()
        self.forward_button.disabled = False
        self.backward_button.disabled = False
        self.first_button.disabled = False
        self.last_button.disabled = False
        if max_pages == 1:
            self.forward_button.disabled = True
            self.backward_button.disabled = True
            self.first_button.disabled = True
            self.last_button.disabled = True
        elif max_pages == 2:
            self.first_button.disabled = True
            self.last_button.disabled = True


class PromptYesOrNo(discord.ui.View):
    ctx: DISCORD_CONTEXT_TYPE
    message: discord.Message
    author: discord.abc.User
    response: bool

    def __init__(self, cog: DISCORD_COG_TYPE, initial_message: str, *, timeout: int = 120) -> None:
        super().__init__(timeout=timeout)
        self.cog = cog
        self.initial_message_str = initial_message
        self.yes_button = YesButton(
            style=discord.ButtonStyle.green,
            row=0,
            cog=cog,
        )
        self.no_button = NoButton(
            style=discord.ButtonStyle.red,
            row=0,
            cog=cog,
        )
        self.add_item(self.yes_button)
        self.add_item(self.no_button)
        self._running = True
        self.message = None  # type: ignore
        self.ctx = None  # type: ignore
        self.author = None  # type: ignore
        self.response = None  # type: ignore

    async def on_timeout(self):
        self._running = False
        if self.message is None:
            return
        with contextlib.suppress(discord.HTTPException):
            if not self.message.flags.ephemeral:
                await self.message.delete()
            else:
                await self.message.edit(view=None)

    async def start(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE):
        if isinstance(ctx, discord.Interaction):
            ctx = await self.cog.bot.get_context(ctx)
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer(ephemeral=True)
        self.ctx = ctx
        await self.send_initial_message(ctx)

    async def send_initial_message(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE):
        self.author = ctx.user if isinstance(ctx, discord.Interaction) else ctx.author
        self.ctx = ctx
        self.message = await ctx.send(
            embed=await self.cog.pylav.construct_embed(description=self.initial_message_str, messageable=ctx),
            view=self,
            ephemeral=True,
        )
        return self.message

    async def wait_for_yes_no(self, wait_for: float = None) -> bool:
        tasks = [asyncio.create_task(c) for c in [self.yes_button.responded.wait(), self.no_button.responded.wait()]]
        done, pending = await asyncio.wait(tasks, timeout=wait_for or self.timeout, return_when=asyncio.FIRST_COMPLETED)
        self.stop()
        for task in pending:
            task.cancel()
        if done:
            done.pop().result()
        if not self.message.flags.ephemeral:
            await self.message.delete()
        else:
            await self.message.edit(view=None)
        self.response = bool(self.yes_button.responded.is_set())
        return self.response

    def stop(self):
        super().stop()
        asyncio.ensure_future(self.on_timeout())


class EntryPickerMenu(BaseMenu):
    _source: EntryPickerSource
    result: Any

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        bot: DISCORD_BOT_TYPE,
        source: EntryPickerSource,
        selector_text: str,
        selector_cls: type[EntrySelectSelector],  # noqa
        original_author: discord.abc.User,
        *,
        clear_buttons_after: bool = False,
        delete_after_timeout: bool = True,
        timeout: int = 120,
        message: discord.Message = None,
        starting_page: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            cog,
            bot,
            source,
            clear_buttons_after=clear_buttons_after,
            delete_after_timeout=delete_after_timeout,
            timeout=timeout,
            message=message,
            starting_page=starting_page,
            **kwargs,
        )
        self.result: Any = None
        self.selector_cls = selector_cls
        self.selector_text = shorten_string(max_length=100, string=selector_text)
        self.forward_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=1,
            row=4,
            cog=cog,
        )
        self.backward_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=-1,
            row=4,
            cog=cog,
        )
        self.first_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}",
            direction=0,
            row=4,
            cog=cog,
        )
        self.last_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}",
            direction=self.source.get_max_pages,
            row=4,
            cog=cog,
        )
        self.close_button = CloseButton(
            style=discord.ButtonStyle.red,
            row=4,
            cog=cog,
        )
        self.refresh_button = RefreshButton(
            style=discord.ButtonStyle.grey,
            row=4,
            cog=cog,
        )
        self.select_view: EntrySelectSelector | None = None
        self.author = original_author

    @property
    def source(self) -> EntryPickerSource:
        return self._source

    async def prepare(self):
        self.clear_items()
        max_pages = self.source.get_max_pages()
        self.forward_button.disabled = False
        self.backward_button.disabled = False
        self.first_button.disabled = False
        self.last_button.disabled = False
        if max_pages == 1:
            self.forward_button.disabled = True
            self.backward_button.disabled = True
            self.first_button.disabled = True
            self.last_button.disabled = True
        elif max_pages == 2:
            self.first_button.disabled = True
            self.last_button.disabled = True
        self.add_item(self.close_button)
        self.add_item(self.first_button)
        self.add_item(self.backward_button)
        self.add_item(self.forward_button)
        self.add_item(self.last_button)
        if self.source.select_options:
            options = self.source.select_options
            self.remove_item(self.select_view)
            self.select_view = self.selector_cls(options, self.cog, self.selector_text, self.source.select_mapping)
            self.add_item(self.select_view)
        if self.select_view and not self.source.select_options:
            self.remove_item(self.select_view)
            self.select_view = None

    async def start(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE):
        if isinstance(ctx, discord.Interaction):
            ctx = await self.cog.bot.get_context(ctx)
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer(ephemeral=True)
        self.ctx = ctx
        await self.send_initial_message(ctx)

    async def show_page(self, page_number: int, interaction: DISCORD_INTERACTION_TYPE):
        await self._source.get_page(page_number)
        await self.prepare()
        self.current_page = page_number
        if self.message is not None:
            if not interaction.response.is_done():
                await interaction.response.pong()
            await self.message.edit(view=self)
        elif not interaction.response.is_done():
            await interaction.response.edit_message(view=self)

    async def wait_for_response(self):
        if isinstance(self.select_view, EntrySelectSelector):
            await asyncio.wait_for(self.select_view.responded.wait(), timeout=self.timeout)
            self.result = self.select_view.entry
