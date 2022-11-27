from __future__ import annotations

from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav.tracks import Track

_ = Translator("PyLavShared", Path(__file__))


class QueueTrackOption(discord.SelectOption):
    def __init__(self, name: str, description: str, value: str):
        super().__init__(
            label=name,
            description=description,
            value=value,
        )

    @classmethod
    async def from_track(cls, track: Track, index: int):
        name = await track.get_track_display_name(
            max_length=100 - (2 + len(str(index + 1))), author=False, unformatted=True
        )
        label = f"{index + 1}. {name}"
        return cls(
            name=label,
            description=track.author,
            value=track.id,
        )


class EffectsOption(discord.SelectOption):
    def __init__(self, label: str, description: str, value: str, index: int):
        super().__init__(
            label=f"{index + 1}. {label}",
            description=description,
            value=value,
        )


class SearchTrackOption(discord.SelectOption):
    def __init__(self, name: str, description: str, value: str):
        super().__init__(
            label=name,
            description=description,
            value=value,
        )

    @classmethod
    async def from_track(cls, track: Track, index: int):
        name = await track.get_track_display_name(
            max_length=100 - (2 + len(str(index + 1))), author=False, unformatted=True
        )
        return cls(name=f"{index + 1}. {name}", description=track.author, value=track.id)
