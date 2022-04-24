from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from pylav.types import ContextT

if TYPE_CHECKING:
    from pylav.query import Query

    QueryConverter = Query
    QueryPlaylistConverter = Query
else:

    class QueryConverter(commands.Converter):
        async def convert(self, ctx: ContextT, arg: str) -> Query:
            from pylav.query import Query

            arg = arg.strip("<>")
            return await Query.from_string(arg)

    class QueryPlaylistConverter(commands.Converter):
        async def convert(self, ctx: ContextT, arg: str) -> Query:
            from pylav.query import Query

            arg = arg.strip("<>")
            query = await Query.from_string(arg)
            if not (query.is_playlist or query.is_album):
                raise commands.BadArgument("Query must be a playlist or album.")
            return query
