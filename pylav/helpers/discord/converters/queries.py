from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from discord.app_commands import Choice, Transformer
from discord.ext import commands

from pylav.players.query.obj import Query
from pylav.type_hints.bot import DISCORD_CONTEXT_TYPE, DISCORD_INTERACTION_TYPE

try:
    from redbot.core.i18n import Translator  # type: ignore

    _ = Translator("PyLav", Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


if TYPE_CHECKING:
    QueryConverter = Query
    QueryPlaylistConverter = Query
else:

    class QueryConverter(Transformer):
        """Converts a query to a Query object"""

        @classmethod
        async def convert(cls, ctx: DISCORD_CONTEXT_TYPE, arg: str) -> Query:  # noqa
            """Converts a query to a Query object"""
            arg = arg.strip("<>")
            return await Query.from_string(arg)

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> Query:
            """Transforms a query to a Query object"""
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        async def autocomplete(self, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            """Autocompletes a query to a Query object"""
            return []

    class QueryPlaylistConverter(Transformer):
        """Converts a query to a Query object"""

        @classmethod
        async def convert(cls, ctx: DISCORD_CONTEXT_TYPE, arg: str) -> Query:  # noqa
            """Converts a query to a Query object"""
            arg = arg.strip("<>")
            query = await Query.from_string(arg)
            if not (query.is_playlist or query.is_album):
                raise commands.BadArgument(_("The query must be a playlist or album."))
            return query

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> Query:
            """Transforms a query to a Query object"""
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        async def autocomplete(self, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            """Autocompletes a query to a Query object"""
            return []
