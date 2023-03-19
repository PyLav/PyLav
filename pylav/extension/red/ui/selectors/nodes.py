from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_list

from pylav.constants.node_features import SUPPORTED_FEATURES, SUPPORTED_SOURCES
from pylav.extension.red.ui.selectors.options.nodes import SOURCE_OPTIONS, NodeOption
from pylav.helpers.format.strings import shorten_string
from pylav.nodes.node import Node
from pylav.storage.models.node.real import Node as NodeModel
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

if TYPE_CHECKING:
    from pylav.extension.red.ui.menus.nodes import AddNodeFlow

_ = Translator("PyLav", Path(__file__))


class SourceSelector(discord.ui.Select):
    view: AddNodeFlow

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        row: int | None = None,
        placeholder: str = "",
    ):
        super().__init__(
            min_values=1,
            max_values=len(SUPPORTED_SOURCES.union(SUPPORTED_FEATURES)),
            options=SOURCE_OPTIONS,
            placeholder=shorten_string(max_length=100, string=placeholder),
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if self.view.author.id != interaction.user.id:
            await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=await self.cog.pylav.construct_embed(
                messageable=interaction,
                description=_("Disabling the following sources: {sources_list_variable_do_not_translate}.").format(
                    sources_list_variable_do_not_translate=humanize_list(self.values)
                ),
            ),
            ephemeral=True,
        )


class NodeSelectSelector(discord.ui.Select):
    def __init__(
        self,
        options: list[NodeOption],
        cog: DISCORD_COG_TYPE,
        placeholder: str,
        mapping: dict[str, Node],
    ):
        super().__init__(
            min_values=1,
            max_values=1,
            options=options,
            placeholder=shorten_string(max_length=100, string=placeholder),
        )
        self.cog = cog
        self.mapping = mapping
        self.node: NodeModel = None  # type:ignore
        self.responded = asyncio.Event()

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        playlist_id = self.values[0]
        self.node: Node = self.mapping.get(playlist_id)
        if self.node is None:
            await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(messageable=interaction, title=_("Node was not found.")),
                ephemeral=True,
            )
            self.view.stop()
            await self.view.on_timeout()
            return
        self.responded.set()
        self.view.stop()
        await self.view.on_timeout()
