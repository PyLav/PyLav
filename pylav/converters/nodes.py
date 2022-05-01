from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from discord.ext import commands

from pylav.types import ContextT

if TYPE_CHECKING:
    from pylav.sql.models import NodeModel

    NodeConverter = TypeVar("NodeConverter", bound=list[NodeModel])
else:

    class NodeConverter(commands.Converter):
        async def convert(self, ctx: ContextT, arg: str) -> list[NodeModel]:
            """Converts a node name or ID to a list of matching objects."""
            from pylav import EntryNotFoundError

            try:
                nodes = await ctx.lavalink.node_db_manager.get_all_nodes()
            except EntryNotFoundError:
                raise commands.BadArgument(f"Node with name or id `{arg}` not found.")
            if r := list(filter(lambda n: arg.lower() in n.name.lower() or arg == f"{n.id}", nodes)):
                return r
            raise commands.BadArgument(f"Node with name or id `{arg}` not found.")
