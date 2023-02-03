from __future__ import annotations

from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav.helpers.format.strings import shorten_string
from pylav.storage.models.playlist import Playlist
from pylav.type_hints.bot import DISCORD_BOT_TYPE

_ = Translator("PyLav", Path(__file__))


class PlaylistOption(discord.SelectOption):
    @classmethod
    async def from_playlist(cls, playlist: Playlist, bot: DISCORD_BOT_TYPE, index: int):
        return cls(
            label=shorten_string(max_length=100, string=f"{index + 1}. {await playlist.fetch_name()}"),
            description=shorten_string(
                max_length=100,
                string=_(
                    "Tracks: {playlist_size_variable_do_not_translate} || {playlist_author_name_variable_do_not_translate} || {playlist_scope_variable_do_not_translate}"
                ).format(
                    playlist_size_variable_do_not_translate=await playlist.size(),
                    playlist_author_name_variable_do_not_translate=await playlist.get_author_name(bot, mention=False),
                    playlist_scope_variable_do_not_translate=await playlist.get_scope_name(bot, mention=False),
                ),
            ),
            value=f"{playlist.id}",
        )
