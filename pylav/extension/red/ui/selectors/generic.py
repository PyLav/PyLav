from __future__ import annotations

import asyncio

import discord

from pylav.extension.red.ui.selectors.options.generic import EntryOption
from pylav.helpers.format.strings import shorten_string
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE
from pylav.type_hints.generics import ANY_GENERIC_TYPE


class EntrySelectSelector(discord.ui.Select):
    def __init__(
        self,
        options: list[EntryOption],
        cog: DISCORD_COG_TYPE,
        placeholder: str,
        mapping: dict[str, ANY_GENERIC_TYPE],
    ):
        super().__init__(
            min_values=1,
            max_values=1,
            options=options,
            placeholder=shorten_string(max_length=100, string=placeholder),
        )
        self.cog = cog
        self.mapping = mapping
        self.entry: ANY_GENERIC_TYPE = None
        self.responded = asyncio.Event()

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE) -> None:
        entry_id = self.values[0]
        self.entry: ANY_GENERIC_TYPE = self.mapping.get(entry_id)
        self.responded.set()
        self.view.stop()
        await self.view.on_timeout()
