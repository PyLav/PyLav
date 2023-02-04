from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Any

import discord
from redbot.core.i18n import Translator

from pylav.constants.playlists import BUNDLED_PLAYLIST_IDS
from pylav.core.context import PyLavContext
from pylav.extension.red.ui.buttons.generic import CloseButton, DoneButton, NavigateButton, RefreshButton
from pylav.extension.red.ui.buttons.playlist import (
    EnqueuePlaylistButton,
    PlaylistClearButton,
    PlaylistDedupeButton,
    PlaylistDeleteButton,
    PlaylistDownloadButton,
    PlaylistInfoButton,
    PlaylistQueueButton,
    PlaylistUpdateButton,
    PlaylistUpsertButton,
)
from pylav.extension.red.ui.menus.generic import BaseMenu
from pylav.extension.red.ui.modals.generic import PromptForInput
from pylav.extension.red.ui.selectors.playlist import PlaylistPlaySelector, PlaylistSelectSelector
from pylav.extension.red.ui.sources.playlist import PlaylistPickerSource
from pylav.helpers import emojis
from pylav.helpers.format.strings import shorten_string
from pylav.storage.models.playlist import Playlist
from pylav.type_hints.bot import DISCORD_BOT_TYPE, DISCORD_COG_TYPE, DISCORD_CONTEXT_TYPE, DISCORD_INTERACTION_TYPE

_ = Translator("PyLav", Path(__file__))


class PlaylistPickerMenu(BaseMenu):
    _source: PlaylistPickerSource
    result: Playlist

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        bot: DISCORD_BOT_TYPE,
        source: PlaylistPickerSource,
        selector_text: str,
        selector_cls: type[PlaylistPlaySelector] | type[PlaylistSelectSelector],  # noqa
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
        self.result: Playlist | None = None
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
        self.select_view: PlaylistPlaySelector | PlaylistSelectSelector | None = None
        self.author = original_author

    @property
    def source(self) -> PlaylistPickerSource:
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
        if isinstance(self.select_view, PlaylistSelectSelector):
            await asyncio.wait_for(self.select_view.responded.wait(), timeout=self.timeout)
            self.result = self.select_view.playlist


class PlaylistCreationFlow(discord.ui.View):
    ctx: DISCORD_CONTEXT_TYPE
    message: discord.Message
    url_prompt: PromptForInput
    name_prompt: PromptForInput
    scope_prompt: PromptForInput
    author: discord.abc.User

    def __init__(self, cog: DISCORD_COG_TYPE, original_author: discord.abc.User, *, timeout: int = 120) -> None:
        super().__init__(timeout=timeout)

        self.cog = cog
        self.bot = cog.bot
        self.author = original_author
        self.url_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Please enter the playlist URL.")),
            label=shorten_string(max_length=100, string=_("Playlist URL")),
            style=discord.TextStyle.paragraph,
            max_length=4000,
        )
        self.name_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Please enter the playlist name.")),
            label=shorten_string(max_length=100, string=_("Playlist Name")),
            max_length=64,
        )

        self.name_button = PlaylistUpsertButton(
            style=discord.ButtonStyle.grey,
            row=0,
            cog=cog,
            emoji=emojis.NAME,
            op="name",
        )
        self.url_button = PlaylistUpsertButton(
            style=discord.ButtonStyle.grey,
            row=0,
            cog=cog,
            emoji=emojis.URL,
            op="url",
        )
        self.done_button = DoneButton(
            style=discord.ButtonStyle.green,
            row=0,
            cog=cog,
        )
        self.queue_button = PlaylistQueueButton(
            style=discord.ButtonStyle.green,
            row=0,
            cog=cog,
            emoji=emojis.QUEUE,
        )
        self.close_button = CloseButton(
            style=discord.ButtonStyle.red,
            row=0,
            cog=cog,
        )

        self.name = None
        self.url = None
        self.scope = None
        self.done = False
        self.queue = None
        self.add_item(self.done_button)
        self.add_item(self.close_button)
        self.add_item(self.name_button)
        self.add_item(self.url_button)
        self.add_item(self.queue_button)

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

    async def start(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE, description: str = None, title: str = None):
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

    async def prompt_url(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        await interaction.response.send_modal(self.url_prompt)
        await self.url_prompt.responded.wait()
        self.url = self.url_prompt.response

    async def prompt_name(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        await interaction.response.send_modal(self.name_prompt)
        await self.name_prompt.responded.wait()

        self.name = self.name_prompt.response

    async def prompt_scope(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        await interaction.response.send_modal(self.scope_prompt)
        await self.scope_prompt.responded.wait()
        self.scope = self.scope_prompt.response

    async def on_timeout(self):
        if self.message is None:
            return
        with contextlib.suppress(discord.HTTPException):
            if not self.message.flags.ephemeral:
                await self.message.delete()
            else:
                await self.message.edit(view=None)

    def stop(self):
        super().stop()
        asyncio.ensure_future(self.on_timeout())


class PlaylistManageFlow(discord.ui.View):
    ctx: DISCORD_CONTEXT_TYPE
    message: discord.Message
    url_prompt: PromptForInput
    name_prompt: PromptForInput
    scope_prompt: PromptForInput
    author: discord.abc.User

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        original_author: discord.abc.User,
        playlist: Playlist,
        *,
        timeout: int = 120,
        manageable: bool = True,
    ) -> None:
        super().__init__(timeout=timeout)

        self.completed = asyncio.Event()
        self.cog = cog
        self.bot = cog.bot
        self.author = original_author
        self.playlist = playlist
        self.url_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Please enter the new URL for this playlist.")),
            label=shorten_string(max_length=100, string=_("Playlist URL")),
            style=discord.TextStyle.paragraph,
            max_length=4000,
        )
        self.name_prompt = PromptForInput(
            cog=self.cog,
            title=shorten_string(max_length=100, string=_("Please enter the new name for this playlist.")),
            label=shorten_string(max_length=100, string=_("Playlist Name")),
            max_length=64,
        )

        self.add_prompt = PromptForInput(
            cog=self.cog,
            title=_("What is the query to add to this playlist?"),
            label=_("Query"),
            style=discord.TextStyle.paragraph,
            max_length=4000,
        )

        self.remove_prompt = PromptForInput(
            cog=self.cog,
            title=_("What is the query to remove from this playlist?"),
            label=_("Query"),
            style=discord.TextStyle.paragraph,
            max_length=4000,
        )

        self.name_button = PlaylistUpsertButton(
            style=discord.ButtonStyle.grey,
            cog=cog,
            emoji=emojis.NAME,
            op="name",
        )
        self.url_button = PlaylistUpsertButton(
            style=discord.ButtonStyle.grey,
            cog=cog,
            emoji=emojis.URL,
            op="url",
        )
        self.add_button = PlaylistUpsertButton(
            style=discord.ButtonStyle.green,
            cog=cog,
            op="add",
            emoji=emojis.PLUS,
        )
        self.remove_button = PlaylistUpsertButton(
            style=discord.ButtonStyle.red,
            cog=cog,
            op="remove",
            emoji=emojis.MINUS,
        )

        self.done_button = DoneButton(
            style=discord.ButtonStyle.green,
            cog=cog,
        )
        self.delete_button = PlaylistDeleteButton(
            style=discord.ButtonStyle.red,
            cog=cog,
        )
        self.clear_button = PlaylistClearButton(
            style=discord.ButtonStyle.red,
            cog=cog,
        )
        self.close_button = CloseButton(
            style=discord.ButtonStyle.red,
            cog=cog,
        )
        self.update_button = PlaylistUpdateButton(
            style=discord.ButtonStyle.green,
            cog=cog,
        )

        self.download_button = PlaylistDownloadButton(
            style=discord.ButtonStyle.blurple,
            cog=cog,
            emoji=emojis.DOWNLOAD,
        )

        self.playlist_enqueue_button = EnqueuePlaylistButton(
            cog=cog,
            style=discord.ButtonStyle.blurple,
            emoji=emojis.PLAYLIST,
            playlist=playlist,
        )
        self.playlist_info_button = PlaylistInfoButton(
            cog=cog,
            style=discord.ButtonStyle.blurple,
            emoji=emojis.INFO,
            playlist=playlist,
        )
        self.queue_button = PlaylistQueueButton(
            style=discord.ButtonStyle.green,
            cog=cog,
            emoji=emojis.QUEUE,
        )
        self.dedupe_button = PlaylistDedupeButton(
            style=discord.ButtonStyle.red,
            cog=cog,
            emoji=emojis.DUPLICATE,
        )

        self.name = None
        self.url = None
        self.scope = None
        self.add_tracks = set()
        self.remove_tracks = set()

        self.clear = None
        self.delete = None
        self.cancelled = True
        self.done = False
        self.update = False
        self.queue = None
        self.dedupe = None
        if manageable or self.playlist.id in BUNDLED_PLAYLIST_IDS:
            self.add_item(self.done_button)
        self.add_item(self.close_button)
        if manageable:
            self.add_item(self.delete_button)
            self.add_item(self.clear_button)
        self.add_item(self.update_button)
        if manageable:
            self.add_item(self.name_button)
            self.add_item(self.url_button)
            self.add_item(self.add_button)
            self.add_item(self.remove_button)
        self.add_item(self.download_button)

        self.add_item(self.playlist_enqueue_button)
        self.add_item(self.playlist_info_button)
        if manageable:
            self.add_item(self.queue_button)
            self.add_item(self.dedupe_button)

    async def send_initial_message(
        self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE, description: str = None, title: str = None
    ):
        self.ctx = ctx
        if not ctx.channel.permissions_for(ctx.me).attach_files:
            self.download_button.disabled = True
        self.message = await ctx.send(
            embed=await self.cog.pylav.construct_embed(description=description, title=title, messageable=ctx),
            view=self,
            ephemeral=True,
        )
        return self.message

    async def start(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE, description: str = None, title: str = None):
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

    async def prompt_url(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.url_prompt)
        await self.url_prompt.responded.wait()
        self.url = self.url_prompt.response

    async def prompt_name(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.name_prompt)
        await self.name_prompt.responded.wait()

        self.name = self.name_prompt.response

    async def prompt_scope(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.scope_prompt)
        await self.scope_prompt.responded.wait()
        self.scope = self.scope_prompt.response

    async def prompt_add_tracks(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.add_prompt)
        await self.add_prompt.responded.wait()
        self.add_tracks.add(self.add_prompt.response)

    async def prompt_remove_tracks(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        self.cancelled = False
        await interaction.response.send_modal(self.remove_prompt)
        await self.remove_prompt.responded.wait()
        self.remove_tracks.add(self.remove_prompt.response)

    async def on_timeout(self):
        self.completed.set()
        if self.message is None:
            return
        with contextlib.suppress(discord.HTTPException):
            if not self.message.flags.ephemeral:
                await self.message.delete()
            else:
                await self.message.edit(view=None)

    def stop(self):
        super().stop()
        asyncio.ensure_future(self.on_timeout())
