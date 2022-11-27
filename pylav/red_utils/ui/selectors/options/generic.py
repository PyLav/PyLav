from __future__ import annotations

import discord

from pylav.red_utils.types import GenericT


class EntryOption(discord.SelectOption):
    @classmethod
    async def from_entry(cls, entry: GenericT, index: int):
        return cls(
            label=f"{index + 1}. {entry.name}",
            value=f"{entry.id}",
        )
