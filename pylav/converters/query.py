from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from pylav.query import Query

    QueryConverter = Query
    QueryPlaylistConverter = Query
else:

    class QueryConverter(commands.Converter):
        async def convert(self, ctx: commands.Context, arg: str) -> Query:
            from pylav.query import Query

            return await Query.from_string(arg)

    class QueryPlaylistConverter(commands.Converter):
        async def convert(self, ctx: commands.Context, arg: str) -> Query:
            from pylav.query import Query

            query = await Query.from_string(arg)
            if not (query.is_playlist or query.is_album):
                raise commands.BadArgument("Query must be a playlist or album.")
            return query
