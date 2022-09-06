from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

import asyncstdlib
from asyncstdlib import heapq
from discord.app_commands import Choice, Transformer
from discord.ext import commands
from rapidfuzz import fuzz

from pylav.exceptions import EntryNotFoundError
from pylav.node import Node
from pylav.types import ContextT, InteractionT
from pylav.utils import shorten_string

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLavPlayer", Path(__file__))
except ImportError:
    _ = lambda x: x

if TYPE_CHECKING:

    NodeConverter = TypeVar("NodeConverter", bound=list[Node])
else:

    class NodeConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[Node]:
            """Converts a node name or ID to a list of matching objects"""
            try:
                nodes = ctx.lavalink.node_manager.nodes
            except EntryNotFoundError as e:
                raise commands.BadArgument(_("Node with name or id `{arg}` not found").format(arg=arg)) from e
            if r := await asyncstdlib.list(
                asyncstdlib.filter(lambda n: arg.lower() in n.name.lower() or arg == f"{n.identifier}", nodes)
            ):
                return r
            raise commands.BadArgument(_("Node with name or id `{arg}` not found").format(arg=arg))

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[Node]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            nodes = interaction.client.lavalink.node_manager.nodes
            if not current:
                return [Choice(name=shorten_string(e.name, max_length=100), value=f"{e.identifier}") for e in nodes][
                    :25
                ]

            async def _filter(c):
                return await asyncio.to_thread(fuzz.partial_ratio, c.name, current)

            extracted = await heapq.nlargest(asyncstdlib.iter(nodes), n=25, key=_filter)

            return [Choice(name=shorten_string(e.name, max_length=100), value=f"{e.identifier}") for e in extracted]
