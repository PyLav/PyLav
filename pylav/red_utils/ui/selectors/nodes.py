from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_list

from pylav.constants import SUPPORTED_FEATURES, SUPPORTED_SOURCES
from pylav.red_utils.ui.selectors.options.nodes import SOURCE_OPTIONS, NodeOption
from pylav.sql.models import NodeModel
from pylav.types import CogT, InteractionT
from pylav.utils import translation_shortener

if TYPE_CHECKING:
    from pylav.red_utils.ui.menus.nodes import AddNodeFlow

_ = Translator("PyLav", Path(__file__))


class SourceSelector(discord.ui.Select):
    view: AddNodeFlow

    def __init__(
        self,
        cog: CogT,
        row: int | None = None,
        placeholder: str = "",
    ):
        super().__init__(
            min_values=1,
            max_values=len(SUPPORTED_SOURCES.union(SUPPORTED_FEATURES)),
            options=SOURCE_OPTIONS,
            placeholder=translation_shortener(max_length=100, translation=placeholder),
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: InteractionT):
        if self.view.author.id != interaction.user.id:
            await interaction.response.send_message(
                embed=await self.cog.lavalink.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option")
                ),
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=await self.cog.lavalink.construct_embed(
                messageable=interaction,
                description=_("Disabling the following sources: {sources}").format(sources=humanize_list(self.values)),
            ),
            ephemeral=True,
        )


class NodeSelectSelector(discord.ui.Select):
    def __init__(
        self,
        options: list[NodeOption],
        cog: CogT,
        placeholder: str,
        mapping: dict[str, NodeModel],
    ):
        super().__init__(
            min_values=1,
            max_values=1,
            options=options,
            placeholder=translation_shortener(max_length=100, translation=placeholder),
        )
        self.cog = cog
        self.mapping = mapping
        self.node: NodeModel = None  # type:ignore
        self.responded = asyncio.Event()

    async def callback(self, interaction: InteractionT):
        playlist_id = self.values[0]
        self.node: NodeModel = self.mapping.get(playlist_id)
        if self.node is None:
            await interaction.response.send_message(
                embed=await self.cog.lavalink.construct_embed(messageable=interaction, title=_("Node not found")),
                ephemeral=True,
            )
            self.view.stop()
            await self.view.on_timeout()
            return
        self.responded.set()
        self.view.stop()
        await self.view.on_timeout()
