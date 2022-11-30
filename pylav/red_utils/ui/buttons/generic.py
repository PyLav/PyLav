from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

import discord
from redbot.core.i18n import Translator

from pylav import emojis
from pylav.types import CogT, InteractionT
from pylav.utils import translation_shortener

_ = Translator("PyLav", Path(__file__))


class NavigateButton(discord.ui.Button):
    def __init__(
        self,
        cog: CogT,
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

    async def callback(self, interaction: InteractionT):
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
        if not interaction.response.is_done():
            await interaction.response.edit_message(view=self.view, **kwargs)
        else:
            await interaction.edit_original_response(view=self.view, **kwargs)


class CloseButton(discord.ui.Button):
    def __init__(self, cog: CogT, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.MINIMIZE,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: InteractionT):
        if self.view.author.id != interaction.user.id:
            return await interaction.response.send_message(
                embed=await self.cog.lavalink.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option")
                ),
                ephemeral=True,
            )
        self.view.cancelled = True
        self.view.stop()
        await self.view.on_timeout()


class YesButton(discord.ui.Button):
    interaction: InteractionT

    def __init__(self, cog: CogT, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style, emoji=None, row=row, label=translation_shortener(max_length=100, translation=_("Yes"))
        )
        self.responded = asyncio.Event()
        self.cog = cog
        self.interaction = None  # type: ignore

    async def callback(self, interaction: InteractionT):
        if self.view.author.id != interaction.user.id:
            await interaction.response.send_message(
                embed=await self.cog.lavalink.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option")
                ),
                ephemeral=True,
            )
            return

        self.responded.set()
        self.interaction = interaction


class NoButton(discord.ui.Button):
    interaction: InteractionT

    def __init__(self, cog: CogT, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style, emoji=None, row=row, label=translation_shortener(max_length=100, translation=_("No"))
        )
        self.responded = asyncio.Event()
        self.cog = cog
        self.interaction = None  # type: ignore

    async def callback(self, interaction: InteractionT):
        if self.view.author.id != interaction.user.id:
            await interaction.response.send_message(
                embed=await self.cog.lavalink.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option")
                ),
                ephemeral=True,
            )
            return
        self.responded.set()
        self.interaction = interaction


class DoneButton(discord.ui.Button):
    def __init__(self, cog: CogT, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.CHECK,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: InteractionT):
        if self.view.author.id != interaction.user.id:
            return await interaction.response.send_message(
                embed=await self.cog.lavalink.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option")
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
        self.label = _("Disconnect {} {}").format(
            disconnect_type_translation, _("players") if multiple else _("player")
        )


class RefreshButton(discord.ui.Button):
    def __init__(self, cog: CogT, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji="\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}",
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: InteractionT):
        await self.view.prepare()
        kwargs = await self.view.get_page(self.view.current_page)
        if not interaction.response.is_done():
            await interaction.response.edit_message(view=self.view, **kwargs)
        else:
            await interaction.edit_original_response(view=self.view, **kwargs)
