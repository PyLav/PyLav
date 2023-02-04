from __future__ import annotations

import asyncio
import contextlib
import re
import time
from pathlib import Path
from typing import Any

import discord
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import inline

from pylav.constants.builtin_nodes import BUNDLED_NODES_IDS_HOST_MAPPING
from pylav.core.context import PyLavContext
from pylav.extension.red.ui.buttons.generic import CloseButton, DoneButton, NavigateButton, RefreshButton
from pylav.extension.red.ui.buttons.nodes import (
    NodeButton,
    NodeDeleteButton,
    NodeShowEnabledSourcesButton,
    SearchOnlyNodeToggleButton,
    SSLNodeToggleButton,
)
from pylav.extension.red.ui.menus.generic import BaseMenu
from pylav.extension.red.ui.modals.generic import PromptForInput
from pylav.extension.red.ui.selectors.nodes import NodeSelectSelector, SourceSelector
from pylav.extension.red.ui.sources.nodes import NodeManageSource, NodePickerSource
from pylav.helpers import emojis
from pylav.helpers.format.strings import shorten_string
from pylav.storage.models.node.real import Node
from pylav.type_hints.bot import DISCORD_BOT_TYPE, DISCORD_COG_TYPE, DISCORD_CONTEXT_TYPE, DISCORD_INTERACTION_TYPE

URL_REGEX = re.compile(r"^(https?)://(\S+)$")
_ = Translator("PyLav", Path(__file__))


class AddNodeFlow(discord.ui.View):
    ctx: DISCORD_CONTEXT_TYPE
    message: discord.Message
    author: discord.abc.User

    def __init__(self, cog: DISCORD_COG_TYPE, original_author: discord.abc.User):
        super().__init__(timeout=600)

        self.cog = cog
        self.bot = cog.bot
        self.author = original_author
        self.cancelled = True
        self.completed = asyncio.Event()
        self.done_button = DoneButton(
            style=discord.ButtonStyle.green,
            cog=cog,
        )
        self.close_button = CloseButton(
            style=discord.ButtonStyle.red,
            cog=cog,
        )
        self.host_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Enter the domain or IP address of the host.")),
            label=shorten_string(max_length=100, string=_("Host")),
            style=discord.TextStyle.short,
            min_length=4,
            max_length=200,
        )
        self.port_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Enter the host port to connect to.")),
            label=shorten_string(max_length=100, string=_("Port")),
            style=discord.TextStyle.short,
            min_length=2,
            max_length=5,
        )
        self.password_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Enter the node password.")),
            label=shorten_string(max_length=100, string=_("Password")),
            style=discord.TextStyle.short,
            min_length=1,
            max_length=64,
        )
        self.name_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Enter an easy to reference name for the node.")),
            label=shorten_string(max_length=100, string=_("Name")),
            style=discord.TextStyle.short,
            min_length=8,
            max_length=64,
        )
        self.resume_timeout_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Enter a timeout in seconds.")),
            label=shorten_string(max_length=100, string=_("Timeout")),
            style=discord.TextStyle.short,
            min_length=2,
            max_length=4,
        )
        self.search_only_button = SearchOnlyNodeToggleButton(
            cog=self.cog,
            style=discord.ButtonStyle.blurple,
            emoji=emojis.SEARCH,
        )
        self.ssl_button = SSLNodeToggleButton(
            cog=self.cog,
            style=discord.ButtonStyle.blurple,
            emoji=emojis.SSL,
        )
        self.disabled_sources_selector = SourceSelector(
            cog=self.cog, placeholder=shorten_string(max_length=100, string=_("Sources to turn off.")), row=2
        )
        self.name_button = NodeButton(
            cog=self.cog,
            style=discord.ButtonStyle.blurple,
            emoji=emojis.NAME,
            op="name",
            row=1,
        )
        self.host_button = NodeButton(
            cog=self.cog,
            style=discord.ButtonStyle.blurple,
            emoji=emojis.HOST,
            op="host",
            row=1,
        )
        self.port_button = NodeButton(
            cog=self.cog,
            style=discord.ButtonStyle.blurple,
            emoji=emojis.PORT,
            op="port",
            row=1,
        )
        self.password_button = NodeButton(
            cog=self.cog,
            style=discord.ButtonStyle.blurple,
            emoji=emojis.PASSWORD,
            op="password",
            row=1,
        )
        self.timeout_button = NodeButton(
            cog=self.cog,
            style=discord.ButtonStyle.blurple,
            emoji=emojis.TIMEOUT,
            op="timeout",
            row=1,
        )

        self.name = None
        self.host = None
        self.port = None
        self.password = None
        self.resume_timeout = 600
        self.reconnect_attempts = -1
        self.ssl = False
        self.search_only = False
        self.unique_identifier = int(time.time())
        self.done = False

        self.add_item(self.done_button)
        self.add_item(self.close_button)
        self.add_item(self.search_only_button)
        self.add_item(self.ssl_button)

        self.add_item(self.name_button)
        self.add_item(self.host_button)
        self.add_item(self.port_button)
        self.add_item(self.password_button)
        self.add_item(self.timeout_button)

        self.add_item(self.disabled_sources_selector)
        self.last_interaction = None

    def stop(self):
        super().stop()
        asyncio.ensure_future(self.on_timeout())

    async def on_timeout(self):
        self.completed.set()
        if self.message is None:
            return
        with contextlib.suppress(discord.HTTPException):
            if not self.message.flags.ephemeral:
                await self.message.delete()
            else:
                await self.message.edit(view=None)

    async def wait_until_complete(self):
        await asyncio.wait_for(self.completed.wait(), timeout=self.timeout)

    async def start(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE, description: str = None, title: str = None):
        self.unique_identifier = ctx.message.id
        await self.send_initial_message(ctx, description=description, title=title)

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

    async def send_initial_message(
        self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE, description: str = None, title: str = None
    ):
        self.ctx = ctx
        self.message = await ctx.send(
            embed=await self.cog.pylav.construct_embed(description=description, title=title, messageable=ctx),
            view=self,
            ephemeral=True,
        )
        return self.message

    async def prompt_name(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.name_prompt)
        await self.name_prompt.responded.wait()
        self.name = self.name_prompt.response
        await interaction.followup.send(
            embed=await self.cog.pylav.construct_embed(
                description=_("The node name has been set to `{node_name_variable_do_not_translate}`.").format(
                    node_name_variable_do_not_translate=inline(self.name)
                ),
                messageable=interaction,
            ),
            ephemeral=True,
        )

    async def prompt_password(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.password_prompt)
        await self.password_prompt.responded.wait()
        self.password = self.password_prompt.response
        await interaction.followup.send(
            embed=await self.cog.pylav.construct_embed(
                description=_("The node password has been set to `{node_password_variable_do_not_translate}`.").format(
                    node_password_variable_do_not_translate=inline(self.password)
                ),
                messageable=interaction,
            ),
            ephemeral=True,
        )

    async def prompt_host(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.host_prompt)
        await self.host_prompt.responded.wait()
        if match := URL_REGEX.match(self.host_prompt.response):
            protocol = match.group(0)
            self.ssl = protocol == "https"
            self.host = match.group(1)
        else:
            self.host = self.host_prompt.response
        await interaction.followup.send(
            embed=await self.cog.pylav.construct_embed(
                description=_("The node host address has been set to `{node_host_variable_do_not_translate}`.").format(
                    node_host_variable_do_not_translate=inline(self.host)
                ),
                messageable=interaction,
            ),
            ephemeral=True,
        )

    async def prompt_port(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.port_prompt)
        await self.port_prompt.responded.wait()
        try:
            self.port = int(self.port_prompt.response)
        except ValueError:
            self.port = None
        if self.port is None:
            await interaction.followup.send(
                embed=await self.cog.pylav.construct_embed(
                    description=_("The port you specified is invalid."),
                    messageable=interaction,
                ),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                embed=await self.cog.pylav.construct_embed(
                    description=_("The node port has been set to `{node_port_variable_do_not_translate}`.").format(
                        node_port_variable_do_not_translate=inline(f"{self.port}")
                    ),
                    messageable=interaction,
                ),
                ephemeral=True,
            )

    async def prompt_resume_timeout(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.resume_timeout_prompt)
        await self.resume_timeout_prompt.responded.wait()
        try:
            self.resume_timeout = int(self.resume_timeout_prompt.response)
        except ValueError:
            self.resume_timeout = None
        if self.resume_timeout is None:
            await interaction.followup.send(
                embed=await self.cog.pylav.construct_embed(
                    description=_("The timeout you specified is invalid; it must be a number in seconds."),
                    messageable=interaction,
                ),
                ephemeral=True,
            )
        else:
            match self.resume_timeout:
                case 0:
                    message = _("The node timeout has been set to `0` seconds.")
                case 1:
                    message = _("The node timeout has been set to `1` second.")
                case __:
                    message = _(
                        "The node timeout has been set to `{node_timeout_variable_do_not_translate}` seconds."
                    ).format(node_timeout_variable_do_not_translate=inline(f"{self.resume_timeout}"))

            await interaction.followup.send(
                embed=await self.cog.pylav.construct_embed(
                    description=message,
                    messageable=interaction,
                ),
                ephemeral=True,
            )


class NodePickerMenu(BaseMenu):
    _source: NodePickerSource
    result: Node

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        bot: DISCORD_BOT_TYPE,
        source: NodePickerSource,
        selector_text: str,
        selector_cls: type[NodeSelectSelector],  # noqa
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
        self.result: Node | None = None
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
        self.select_view: NodeSelectSelector | None = None
        self.author = original_author

    @property
    def source(self) -> NodePickerSource:
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
        if isinstance(self.select_view, NodeSelectSelector):
            await asyncio.wait_for(self.select_view.responded.wait(), timeout=self.timeout)
            self.result = self.select_view.node


class NodeManagerMenu(BaseMenu):
    _source: NodeManageSource

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        bot: DISCORD_BOT_TYPE,
        source: NodeManageSource,
        original_author: discord.abc.User,
        *,
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
            delete_after_timeout=delete_after_timeout,
            timeout=timeout,
            message=message,
            starting_page=starting_page,
            **kwargs,
        )
        self.unique_identifier = int(time.time())
        self.current_page = -1
        self.forward_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=1,
            cog=cog,
            row=0,
        )
        self.backward_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=-1,
            cog=cog,
            row=0,
        )
        self.first_button = NavigateButton(
            style=discord.ButtonStyle.grey, emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}", direction=0, cog=cog, row=0
        )
        self.last_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}",
            direction=self.source.get_max_pages,
            cog=cog,
            row=0,
        )
        self.close_button = CloseButton(style=discord.ButtonStyle.red, cog=cog, row=0)
        self.host_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Change the domain or IP address of the host.")),
            label=shorten_string(max_length=100, string=_("Host")),
            style=discord.TextStyle.short,
            min_length=4,
            max_length=200,
        )
        self.port_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Change the host port to connect to.")),
            label=shorten_string(max_length=100, string=_("Port")),
            style=discord.TextStyle.short,
            min_length=2,
            max_length=5,
        )
        self.password_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Change the node password.")),
            label=shorten_string(max_length=100, string=_("Password")),
            style=discord.TextStyle.short,
            min_length=1,
            max_length=64,
        )
        self.name_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Change the name of this node.")),
            label=shorten_string(max_length=100, string=_("Name")),
            style=discord.TextStyle.short,
            min_length=8,
            max_length=64,
        )
        self.resume_timeout_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Enter the new timeout for this node.")),
            label=shorten_string(max_length=100, string=_("Timeout")),
            style=discord.TextStyle.short,
            min_length=2,
            max_length=4,
        )
        self.show_sources_button = NodeShowEnabledSourcesButton(cog=self.cog, style=discord.ButtonStyle.blurple, row=1)
        self.done_button = DoneButton(style=discord.ButtonStyle.green, cog=cog, row=1)
        self.search_only_button = SearchOnlyNodeToggleButton(
            cog=self.cog, style=discord.ButtonStyle.blurple, emoji=emojis.SEARCH, row=1
        )
        self.ssl_button = SSLNodeToggleButton(cog=self.cog, style=discord.ButtonStyle.blurple, emoji=emojis.SSL, row=1)

        self.name_button = NodeButton(
            cog=self.cog, style=discord.ButtonStyle.blurple, emoji=emojis.NAME, op="name", row=1
        )
        self.host_button = NodeButton(
            cog=self.cog, style=discord.ButtonStyle.blurple, emoji=emojis.HOST, op="host", row=2
        )
        self.port_button = NodeButton(
            cog=self.cog, style=discord.ButtonStyle.blurple, emoji=emojis.PORT, op="port", row=2
        )
        self.password_button = NodeButton(
            cog=self.cog, style=discord.ButtonStyle.blurple, emoji=emojis.PASSWORD, op="password", row=2
        )
        self.timeout_button = NodeButton(
            cog=self.cog, style=discord.ButtonStyle.blurple, emoji=emojis.TIMEOUT, op="timeout", row=2
        )
        self.delete_button = NodeDeleteButton(cog=self.cog, style=discord.ButtonStyle.red, row=2)
        self.disabled_sources_selector = SourceSelector(
            cog=self.cog, placeholder=shorten_string(max_length=100, string=_("Source to disable.")), row=3
        )

        self.cancelled = True

        self.author = original_author
        self.completed = asyncio.Event()

        self.name = None
        self.host = None
        self.port = None
        self.password = None
        self.resume_timeout = None
        self.ssl = None
        self.search_only = None
        self.done = False
        self.delete = None

    @property
    def source(self) -> NodeManageSource:
        return self._source

    async def prepare(self):
        self.clear_items()
        max_pages = self.source.get_max_pages()
        self.done_button.disabled = False
        self.name_button.disabled = False
        self.host_button.disabled = False
        self.port_button.disabled = False
        self.password_button.disabled = False
        self.timeout_button.disabled = False
        self.disabled_sources_selector.disabled = False
        self.ssl_button.disabled = False
        self.search_only_button.disabled = False
        self.backward_button.disabled = False
        self.forward_button.disabled = False
        self.first_button.disabled = False
        self.last_button.disabled = False
        self.add_item(self.close_button)
        self.add_item(self.first_button)
        self.add_item(self.backward_button)
        self.add_item(self.forward_button)
        self.add_item(self.last_button)
        if max_pages <= 2:
            self.first_button.disabled = True
            self.last_button.disabled = True
        if self.source.target:
            self.add_item(self.show_sources_button)
            if self.source.target.identifier not in BUNDLED_NODES_IDS_HOST_MAPPING:
                self.add_item(self.done_button)
                self.add_item(self.search_only_button)
                self.add_item(self.ssl_button)
                self.add_item(self.name_button)
                self.add_item(self.host_button)
                self.add_item(self.port_button)
                self.add_item(self.password_button)
                self.add_item(self.timeout_button)
                self.add_item(self.delete_button)
                self.add_item(self.disabled_sources_selector)

    def stop(self):
        super().stop()
        asyncio.ensure_future(self.on_timeout())

    async def on_timeout(self):
        self.completed.set()
        if self.message is None:
            return
        with contextlib.suppress(discord.HTTPException):
            if not self.message.flags.ephemeral:
                await self.message.delete()
            else:
                await self.message.edit(view=None)

    async def wait_until_complete(self):
        await asyncio.wait_for(self.completed.wait(), timeout=self.timeout)

    async def start(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE, description: str = None, title: str = None):
        self.unique_identifier = ctx.message.id
        await self.send_initial_message(ctx, description=description, title=title)

    async def interaction_check(self, interaction: DISCORD_INTERACTION_TYPE):
        """Just extends the default reaction_check to use owner_ids"""
        if (not await self.bot.allowed_by_whitelist_blacklist(interaction.user, guild=interaction.guild)) or (
            self.author and (interaction.user.id != self.author.id)
        ):
            await interaction.response.send_message(
                content="You are not authorized to interact with this", ephemeral=True
            )
            return False
        return True

    async def send_initial_message(
        self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE, description: str = None, title: str = None
    ):
        self.ctx = ctx
        await self.prepare()
        self.message = await ctx.send(
            embed=await self.cog.pylav.construct_embed(description=description, title=title, messageable=ctx),
            view=self,
            ephemeral=True,
        )
        return self.message

    async def prompt_name(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.name_prompt)
        await self.name_prompt.responded.wait()
        self.name = self.name_prompt.response
        await interaction.followup.send(
            embed=await self.cog.pylav.construct_embed(
                description=_("The node name has been set to `{node_name_variable_do_not_translate}`.").format(
                    node_name_variable_do_not_translate=inline(self.name)
                ),
                messageable=interaction,
            ),
            ephemeral=True,
        )

    async def prompt_password(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.password_prompt)
        await self.password_prompt.responded.wait()
        self.password = self.password_prompt.response
        await interaction.followup.send(
            embed=await self.cog.pylav.construct_embed(
                description=_("The node password has been set to `{node_password_variable_do_not_translate}`.").format(
                    node_password_variable_do_not_translate=inline(self.password)
                ),
                messageable=interaction,
            ),
            ephemeral=True,
        )

    async def prompt_host(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.host_prompt)
        await self.host_prompt.responded.wait()
        if match := URL_REGEX.match(self.host_prompt.response):
            protocol = match.group(0)
            self.ssl = protocol == "https"
            self.host = match.group(1)
        else:
            self.host = self.host_prompt.response
        await interaction.followup.send(
            embed=await self.cog.pylav.construct_embed(
                description=_("The node host address has been set to `{node_host_variable_do_not_translate}`.").format(
                    node_host_variable_do_not_translate=inline(self.host)
                ),
                messageable=interaction,
            ),
            ephemeral=True,
        )

    async def prompt_port(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.port_prompt)
        await self.port_prompt.responded.wait()
        try:
            self.port = int(self.port_prompt.response)
        except ValueError:
            self.port = None
        if self.port is None:
            await interaction.followup.send(
                embed=await self.cog.pylav.construct_embed(
                    description=_("The port you specified is invalid."),
                    messageable=interaction,
                ),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                embed=await self.cog.pylav.construct_embed(
                    description=_("The node port has been set to `{node_port_variable_do_not_translate}`.").format(
                        node_port_variable_do_not_translate=inline(f"{self.port}")
                    ),
                    messageable=interaction,
                ),
                ephemeral=True,
            )

    async def prompt_resume_timeout(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.resume_timeout_prompt)
        await self.resume_timeout_prompt.responded.wait()
        try:
            self.resume_timeout = int(self.resume_timeout_prompt.response)
        except ValueError:
            self.resume_timeout = None
        if self.resume_timeout is None:
            await interaction.followup.send(
                embed=await self.cog.pylav.construct_embed(
                    description=_("The timeout you specified is invalid; it must be a number in seconds."),
                    messageable=interaction,
                ),
                ephemeral=True,
            )
        else:
            match self.resume_timeout:
                case 1:
                    message = _("The node timeout has been set to `1` second.").format(
                        node_timeout_variable_do_not_translate=inline(f"{self.resume_timeout}")
                    )
                case 0:
                    message = _("The node timeout has been set to `0` seconds.")
                case __:
                    message = _(
                        "The node timeout has been set to `{node_timeout_variable_do_not_translate}` seconds."
                    ).format(node_timeout_variable_do_not_translate=inline(f"{self.resume_timeout}"))

            await interaction.followup.send(
                embed=await self.cog.pylav.construct_embed(
                    description=message,
                    messageable=interaction,
                ),
                ephemeral=True,
            )
