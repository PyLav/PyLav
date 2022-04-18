from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

QUERY_CLS = None


class QueryConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> Query:
        return await QUERY_CLS.from_string(arg)


if TYPE_CHECKING:
    from pylav.query import Query

    QueryConverter = Query
    QUERY_CLS = Query
else:
    QueryConverter = QueryConverter


def __init_import():
    global QUERY_CLS
    from pylav.query import Query as _Query

    QUERY_CLS = _Query


# Stops circular import
__init_import()
