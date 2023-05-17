from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav.helpers import emojis
from pylav.helpers.format.strings import shorten_string
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

_ = Translator("PyLav", Path(__file__))


class NavigateButton(discord.ui.Button):
    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        style: discord.ButtonStyle,
        emoji: str | discord.PartialEmoji,
        direction: int | Callable[[], int],
        row: int = None,
        label: str = None,
    ):
        super().__init__(style=style, emoji=emoji, row=row, label=label)
        self.cog = cog
        self._direction = direction

    @property
    def direction(self) -> int:
        return self._direction if isinstance(self._direction, int) else self._direction()

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        max_pages = self.view.source.get_max_pages()
        if self.direction == 0:
            self.view.current_page = 0
        elif self.direction == max_pages:
            self.view.current_page = max_pages - 1
        else:
            self.view.current_page += self.direction

        if self.view.current_page >= max_pages:
            self.view.current_page = 0
        elif self.view.current_page < 0:
            self.view.current_page = max_pages - 1

        kwargs = await self.view.get_page(self.view.current_page)
        await self.view.prepare()
        attachments = []
        if "file" in kwargs:
            attachments = [kwargs.pop("file")]
        elif "files" in kwargs:
            attachments = kwargs.pop("files")
        if attachments:
            kwargs["attachments"] = attachments
        await self.view.message.edit(view=self.view, **kwargs)


class CloseButton(discord.ui.Button):
    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.MINIMIZE,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if self.view.author.id != interaction.user.id:
            return await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        self.view.cancelled = True
        self.view.stop()
        await self.view.on_timeout()


class YesButton(discord.ui.Button):
    interaction: DISCORD_INTERACTION_TYPE

    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(style=style, emoji=None, row=row, label=shorten_string(max_length=100, string=_("Yes")))
        self.responded = asyncio.Event()
        self.cog = cog
        self.interaction = None  # type: ignore

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if self.view.author.id != interaction.user.id:
            await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
            return
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        self.responded.set()
        self.interaction = interaction


class NoButton(discord.ui.Button):
    interaction: DISCORD_INTERACTION_TYPE

    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(style=style, emoji=None, row=row, label=shorten_string(max_length=100, string=_("No")))
        self.responded = asyncio.Event()
        self.cog = cog
        self.interaction = None  # type: ignore

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if self.view.author.id != interaction.user.id:
            await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
            return
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        self.responded.set()
        self.interaction = interaction


class DoneButton(discord.ui.Button):
    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.CHECK,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if self.view.author.id != interaction.user.id:
            return await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
        self.view.done = True
        self.view.cancelled = False
        self.view.stop()
        await self.view.on_timeout()


class LabelButton(discord.ui.Button):
    def __init__(
        self,
        disconnect_type_translation: str,
        multiple=True,
        row: int = None,
    ):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=None,
            row=row,
        )
        if multiple:
            self.label = _("Disconnect {player_type_variable_do_not_translate} players").format(
                player_type_variable_do_not_translate=disconnect_type_translation
            )
        else:
            self.label = _("Disconnect {player_type_variable_do_not_translate} player").format(
                player_type_variable_do_not_translate=disconnect_type_translation
            )


class RefreshButton(discord.ui.Button):
    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji="\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}",
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        await self.view.prepare()
        kwargs = await self.view.get_page(self.view.current_page)
        attachments = []
        if "file" in kwargs:
            attachments = [kwargs.pop("file")]
        elif "files" in kwargs:
            attachments = kwargs.pop("files")
        if attachments:
            kwargs["attachments"] = attachments
        await self.view.message.edit(view=self.view, **kwargs)
