from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

import asyncstdlib
from discord.app_commands import Choice, Transformer
from discord.ext import commands
from rapidfuzz import fuzz

from pylav.exceptions.database import EntryNotFoundException
from pylav.helpers.format.strings import shorten_string
from pylav.storage.models.playlist import Playlist as PlaylistModel
from pylav.type_hints.bot import DISCORD_CONTEXT_TYPE, DISCORD_INTERACTION_TYPE

try:
    from redbot.core.i18n import Translator  # type: ignore

    _ = Translator("PyLav", Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


if TYPE_CHECKING:
    PlaylistConverter = TypeVar("PlaylistConverter", bound=list[PlaylistModel])
else:

    class PlaylistConverter(Transformer):
        """Converts a playlist name or ID to a list of matching objects"""

        @classmethod
        async def convert(cls, ctx: DISCORD_CONTEXT_TYPE, arg: str) -> list[PlaylistModel]:
            """Converts a playlist name or ID to a list of matching objects"""

            try:
                playlists = await ctx.pylav.playlist_db_manager.get_playlist_by_name_or_id(arg)
            except EntryNotFoundException as e:
                raise commands.BadArgument(
                    _(
                        "A playlist with the name or identifier `{user_input_variable_do_not_translate}` was not found."
                    ).format(user_input_variable_do_not_translate=arg)
                ) from e
            return playlists

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> list[PlaylistModel]:
            """Transforms a playlist name or ID to a list of matching objects"""
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            """Autocompletes a playlist name or ID to a list of matching objects"""
            if not current:
                playlists = await interaction.client.pylav.playlist_db_manager.get_bundled_playlists()
                return [
                    Choice(name=shorten_string(await e.fetch_name(), max_length=100), value=f"{e.id}")
                    for e in playlists
                ][:25]

            try:
                playlists = await interaction.client.pylav.playlist_db_manager.get_playlist_by_name(current, limit=50)
            except EntryNotFoundException:
                return []

            async def _filter(c: PlaylistModel):
                name = await c.fetch_name()
                author = await c.fetch_author()
                return (
                    fuzz.partial_ratio(name, current, score_cutoff=75),
                    1 if author == interaction.user.id else 0,
                    [-ord(i) for i in name],
                )

            extracted = await asyncstdlib.heapq.nlargest(asyncstdlib.iter(playlists), n=25, key=_filter)
            return [
                Choice(name=shorten_string(await e.fetch_name(), max_length=100), value=f"{e.id}") for e in extracted
            ]
