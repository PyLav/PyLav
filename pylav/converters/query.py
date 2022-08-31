from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from discord.app_commands import Choice, Transformer
from discord.ext import commands

from pylav.types import ContextT, InteractionT

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLavPlayer", Path(__file__))
except ImportError:
    _ = lambda x: x

if TYPE_CHECKING:
    from pylav.query import Query

    QueryConverter = Query
    QueryPlaylistConverter = Query
else:

    class QueryConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> Query:
            from pylav.query import Query

            arg = arg.strip("<>")
            return await Query.from_string(arg)

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> Query:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        async def autocomplete(self, interaction: InteractionT, current: str) -> list[Choice]:
            return []

    class QueryPlaylistConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> Query:
            from pylav.query import Query

            arg = arg.strip("<>")
            query = await Query.from_string(arg)
            if not (query.is_playlist or query.is_album):
                raise commands.BadArgument(_("Query must be a playlist or album"))
            return query

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> Query:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        async def autocomplete(self, interaction: InteractionT, current: str) -> list[Choice]:
            return []
