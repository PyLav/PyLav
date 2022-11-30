from __future__ import annotations

import asyncio

import discord

from pylav.red_utils.types import GenericT
from pylav.red_utils.ui.selectors.options.generic import EntryOption
from pylav.types import CogT, InteractionT
from pylav.utils import translation_shortener


class EntrySelectSelector(discord.ui.Select):
    def __init__(
        self,
        options: list[EntryOption],
        cog: CogT,
        placeholder: str,
        mapping: dict[str, GenericT],
    ):
        super().__init__(
            min_values=1,
            max_values=1,
            options=options,
            placeholder=translation_shortener(max_length=100, translation=placeholder),
        )
        self.cog = cog
        self.mapping = mapping
        self.entry: GenericT = None  # type:ignore
        self.responded = asyncio.Event()

    async def callback(self, interaction: InteractionT):
        entry_id = self.values[0]
        self.entry: GenericT = self.mapping.get(entry_id)
        self.responded.set()
        self.view.stop()
        await self.view.on_timeout()
