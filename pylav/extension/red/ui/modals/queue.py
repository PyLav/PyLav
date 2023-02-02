from __future__ import annotations

from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav.helpers.format.strings import shorten_string
from pylav.logging import getLogger
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

LOGGER = getLogger("PyLav.ext.red.ui.modals.queue")
_ = Translator("PyLav", Path(__file__))


class EnqueueModal(discord.ui.Modal):
    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        title: str,
        timeout: float | None = None,
    ):
        super().__init__(title=title, timeout=timeout)
        self.cog = cog
        self.text = discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            label=shorten_string(max_length=100, string=_("Search for a song to add to the queue.")),
            placeholder=shorten_string(
                max_length=100,
                string="Hello by Adele, speak:Hello, https://open.spotify.com/playlist/37i9dQZF1DX6XceWZP1znY",
            ),
        )
        self.add_item(self.text)

    async def on_submit(self, interaction: DISCORD_INTERACTION_TYPE):
        await self.cog.command_play.callback(
            self.cog,
            interaction,
            query=self.text.value.strip(),
        )
