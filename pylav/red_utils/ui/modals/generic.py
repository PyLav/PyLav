from __future__ import annotations

import asyncio

import discord

from pylav import getLogger
from pylav.types import CogT, InteractionT

LOGGER = getLogger("PyLav.ext.Shared.ui.modals.generic")


class PromptForInput(discord.ui.Modal):
    interaction: InteractionT
    response: str

    def __init__(
        self,
        cog: CogT,
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

    async def on_submit(self, interaction: InteractionT):
        self.interaction = interaction
        await interaction.response.defer()
        self.responded.set()
        self.response = self.text.value.strip()
