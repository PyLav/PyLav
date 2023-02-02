from __future__ import annotations

from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav.helpers.format.strings import shorten_string
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

_ = Translator("PyLav", Path(__file__))


class PlaylistSaveModal(discord.ui.Modal):
    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        button: discord.ui.Button,
        title: str,
        timeout: float | None = None,
    ):
        self.cog = cog
        self._button = button
        super().__init__(title=title, timeout=timeout)
        self.text = discord.ui.TextInput(
            style=discord.TextStyle.short,
            label=shorten_string(max_length=100, string=_("Enter the name for the new playlist.")),
            placeholder=shorten_string(max_length=100, string=_("My awesome new playlist")),
            min_length=3,
            max_length=64,
        )
        self.add_item(self.text)

    async def on_submit(self, interaction: DISCORD_INTERACTION_TYPE):
        await self.cog.slash_playlist_save.callback(self.cog, interaction, name=self.text.value.strip())
