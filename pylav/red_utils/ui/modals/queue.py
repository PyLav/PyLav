from __future__ import annotations

from pathlib import Path

import discord
from red_commons.logging import getLogger
from redbot.core.i18n import Translator

from pylav.types import CogT, InteractionT

LOGGER = getLogger("PyLav.ext.Shared.ui.modals.queue")
_ = Translator("PyLavShared", Path(__file__))


class EnqueueModal(discord.ui.Modal):
    def __init__(
        self,
        cog: CogT,
        title: str,
        timeout: float | None = None,
    ):
        super().__init__(title=title, timeout=timeout)
        self.cog = cog
        self.text = discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            label=_("Search for a song to add to the queue"),
            placeholder=_("Hello by Adele, speak:Hello, https://open.spotify.com/playlist/37i9dQZF1DX6XceWZP1znY"),
        )
        self.add_item(self.text)

    async def on_submit(self, interaction: InteractionT):
        await self.cog.command_play.callback(
            self.cog,
            interaction,
            query=self.text.value.strip(),
        )
