from __future__ import annotations

import asyncio

import discord

from pylav.logging import getLogger
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

LOGGER = getLogger("PyLav.ext.red.ui.modals.generic")


class PromptForInput(discord.ui.Modal):
    interaction: DISCORD_INTERACTION_TYPE
    response: str

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        title: str,
        label: str,
        timeout: float | None = None,
        placeholder: str = None,
        style: discord.TextStyle = discord.TextStyle.paragraph,
        min_length: int = 1,
        max_length: int = 64,
        row: int = 1,
    ):
        super().__init__(title=title, timeout=timeout)
        self.cog = cog
        self.text = discord.ui.TextInput(
            label=label, style=style, placeholder=placeholder, min_length=min_length, max_length=max_length, row=row
        )
        self.add_item(self.text)
        self.responded = asyncio.Event()
        self.response = None  # type: ignore
        self.interaction = None  # type: ignore

    async def on_submit(self, interaction: DISCORD_INTERACTION_TYPE):
        self.interaction = interaction
        await interaction.response.defer()
        self.responded.set()
        self.response = self.text.value.strip()
