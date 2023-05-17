from __future__ import annotations

from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav.helpers import emojis
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

_ = Translator("PyLav", Path(__file__))


class EqualizerButton(discord.ui.Button):
    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None) -> None:
        super().__init__(
            style=style,
            emoji=emojis.EQUALIZER,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
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
