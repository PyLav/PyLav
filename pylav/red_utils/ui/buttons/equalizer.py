from __future__ import annotations

from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav import emojis
from pylav.types import CogT, InteractionT

_ = Translator("PyLavShared", Path(__file__))


class EqualizerButton(discord.ui.Button):
    def __init__(self, cog: CogT, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.EQUALIZER,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: InteractionT):
        kwargs = await self.view.get_page(self.view.current_page)
        await self.view.prepare()
        if not interaction.response.is_done():
            await interaction.response.edit_message(view=self.view, **kwargs)
        else:
            await interaction.edit_original_response(view=self.view, **kwargs)
