from __future__ import annotations

import discord

from pylav.red_utils.types import GenericT
from pylav.utils import translation_shortener


class EntryOption(discord.SelectOption):
    @classmethod
    async def from_entry(cls, entry: GenericT, index: int):
        return cls(
            label=translation_shortener(max_length=100, translation=f"{index + 1}. {entry.name}"),
            value=f"{entry.id}",
        )
