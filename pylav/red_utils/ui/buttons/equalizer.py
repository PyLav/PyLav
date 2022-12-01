from __future__ import annotations

from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav import emojis
from pylav.types import CogT, InteractionT

_ = Translator("PyLav", Path(__file__))


class EqualizerButton(discord.ui.Button):
    def __init__(self, cog: CogT, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.EQUALIZER,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: InteractionT):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        kwargs = await self.view.get_page(self.view.current_page)
        await self.view.prepare()
        await self.view.message.edit(view=self.view, **kwargs)
