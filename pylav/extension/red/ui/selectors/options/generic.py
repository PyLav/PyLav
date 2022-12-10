from __future__ import annotations

import discord

from pylav.helpers.format.strings import shorten_string
from pylav.type_hints.generics import ANY_GENERIC_TYPE


class EntryOption(discord.SelectOption):
    @classmethod
    async def from_entry(cls, entry: ANY_GENERIC_TYPE, index: int):
        return cls(
            label=shorten_string(max_length=100, string=f"{index + 1}. {entry.name}"),
            value=f"{entry.id}",
        )
