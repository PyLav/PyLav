from __future__ import annotations

from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav.sql.models import PlaylistModel
from pylav.types import BotT
from pylav.utils import translation_shortener

_ = Translator("PyLav", Path(__file__))


class PlaylistOption(discord.SelectOption):
    @classmethod
    async def from_playlist(cls, playlist: PlaylistModel, bot: BotT, index: int):
        return cls(
            label=translation_shortener(max_length=100, translation=f"{index + 1}. {await playlist.fetch_name()}"),
            description=translation_shortener(
                max_length=100,
                translation=_("Tracks: {} || {} || {}").format(
                    await playlist.size(),
                    await playlist.get_author_name(bot, mention=False),
                    await playlist.get_scope_name(bot, mention=False),
                ),
            ),
            value=f"{playlist.id}",
        )
