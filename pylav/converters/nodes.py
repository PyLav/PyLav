from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import asyncstdlib
from discord.app_commands import Choice, Transformer
from discord.ext import commands

from pylav.node import Node
from pylav.types import ContextT, InteractionT

if TYPE_CHECKING:

    NodeConverter = TypeVar("NodeConverter", bound=list[Node])
else:

    class NodeConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[Node]:
            """Converts a node name or ID to a list of matching objects."""
            from pylav import EntryNotFoundError

            try:
                nodes = ctx.lavalink.node_manager.nodes
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Node with name or id `{arg}` not found.") from e
            if r := await asyncstdlib.list(
                asyncstdlib.filter(lambda n: arg.lower() in n.name.lower() or arg == f"{n.identifier}", nodes)
            ):
                return r
            raise commands.BadArgument(f"Node with name or id `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[Node]:
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            nodes = interaction.client.lavalink.node_manager.nodes

            return [Choice(name=n.name, value=f"{n.identifier}") for n in nodes if current.lower() in n.name.lower()][
                :25
            ]
