from __future__ import annotations

import heapq
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from discord.app_commands import Choice, Transformer
from discord.ext import commands
from rapidfuzz import fuzz

from pylav.exceptions.database import EntryNotFoundException
from pylav.helpers.format.strings import shorten_string
from pylav.nodes.node import Node
from pylav.type_hints.bot import DISCORD_CONTEXT_TYPE, DISCORD_INTERACTION_TYPE

try:
    from redbot.core.i18n import Translator  # type: ignore

    _ = Translator("PyLav", Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


if TYPE_CHECKING:
    NodeConverter = TypeVar("NodeConverter", bound=list[Node])
else:

    class NodeConverter(Transformer):
        """Converts a node name or ID to a list of matching objects"""

        @classmethod
        async def convert(cls, ctx: DISCORD_CONTEXT_TYPE, arg: str) -> list[Node]:
            """Converts a node name or ID to a list of matching objects"""
            try:
                nodes = ctx.pylav.node_manager.nodes
            except EntryNotFoundException as e:
                raise commands.BadArgument(
                    _("Node with name or identifier `{user_input_variable_do_not_translate}` not found.").format(
                        user_input_variable_do_not_translate=arg
                    )
                ) from e
            if r := list(filter(lambda n: arg.lower() in n.name.lower() or arg == f"{n.identifier}", nodes)):
                return r
            raise commands.BadArgument(
                _("Node with name or identifier `{user_input_variable_do_not_translate}` not found").format(
                    user_input_variable_do_not_translate=arg
                )
            )

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> list[Node]:
            """Transforms a node name or ID to a list of matching objects"""
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            """Autocompletes a node name or ID to a list of matching objects"""
            nodes = interaction.client.pylav.node_manager.nodes
            if not current:
                return [Choice(name=shorten_string(e.name, max_length=100), value=f"{e.identifier}") for e in nodes][
                    :25
                ]

            def _filter(c):
                return fuzz.partial_ratio(c.name, current)

            extracted = heapq.nlargest(25, nodes, key=_filter)

            return [Choice(name=shorten_string(e.name, max_length=100), value=f"{e.identifier}") for e in extracted]
