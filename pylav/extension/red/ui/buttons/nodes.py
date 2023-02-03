from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import discord
from discord import Emoji, PartialEmoji
from redbot.core.i18n import Translator

from pylav.helpers import emojis
from pylav.logging import getLogger
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

if TYPE_CHECKING:
    from pylav.extension.red.ui.menus.nodes import AddNodeFlow, NodeManagerMenu


LOGGER = getLogger("PyLav.ext.red.ui.button.nodes")


_ = Translator("PyLav", Path(__file__))


class SSLNodeToggleButton(discord.ui.Button):
    view: AddNodeFlow

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        style: discord.ButtonStyle,
        emoji: str | Emoji | PartialEmoji,
        row: int = None,
    ):
        super().__init__(
            style=style,
            emoji=emoji,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        context = await self.cog.bot.get_context(interaction)
        if self.view.author.id != interaction.user.id:
            return await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
        self.view.ssl = not self.view.ssl
        if self.view.ssl:
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction,
                    description=_(
                        "I will connect to this node using a secure connection. Please ensure that this node supports secure connections."
                    ),
                ),
                ephemeral=True,
            )
        else:
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("I will connect to this node using an unsecure connection.")
                ),
                ephemeral=True,
            )


class SearchOnlyNodeToggleButton(discord.ui.Button):
    view: AddNodeFlow

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        style: discord.ButtonStyle,
        emoji: str | Emoji | PartialEmoji,
        row: int = None,
    ):
        super().__init__(
            style=style,
            emoji=emoji,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        context = await self.cog.bot.get_context(interaction)
        if self.view.author.id != interaction.user.id:
            return await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
        self.view.search_only = not self.view.search_only
        if self.view.search_only:
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("This node will be used for searches only.")
                ),
                ephemeral=True,
            )
        else:
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("This node will be used for both searches and playback.")
                ),
                ephemeral=True,
            )


class AddNodeDoneButton(discord.ui.Button):
    view: AddNodeFlow

    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.CHECK,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        context = await self.cog.bot.get_context(interaction)
        if self.view.author.id != interaction.user.id:
            return await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
        if not ([self.view.name, self.view.host, self.view.port, self.view.password]):
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("Please fill out all the fields before continuing.")
                ),
                ephemeral=True,
            )
            return
        self.view.last_interaction = interaction
        self.view.done = True
        self.view.disabled_sources = self.view.disabled_sources_selector.values
        self.view.cancelled = False
        self.view.stop()
        await self.view.on_timeout()


class NodeButton(discord.ui.Button):
    view: AddNodeFlow

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        style: discord.ButtonStyle,
        op: Literal["name", "host", "port", "password", "timeout"],
        label: str = None,
        emoji: str | Emoji | PartialEmoji = None,
        row: int = None,
    ):
        super().__init__(
            style=style,
            emoji=emoji,
            label=label,
            row=row,
        )
        self.cog = cog
        self.op = op

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if self.view.author.id != interaction.user.id:
            return await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
        self.view.cancelled = False
        if self.op == "name":
            await self.view.prompt_name(interaction)
        elif self.op == "host":
            await self.view.prompt_host(interaction)
        elif self.op == "port":
            await self.view.prompt_port(interaction)
        elif self.op == "password":
            await self.view.prompt_password(interaction)
        elif self.op == "timeout":
            await self.view.prompt_resume_timeout(interaction)


class NodeDeleteButton(discord.ui.Button):
    view: NodeManagerMenu

    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.TRASH,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        context = await self.cog.bot.get_context(interaction)
        if self.view.author.id != interaction.user.id:
            return await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
        self.view.cancelled = False
        self.view.delete = not self.view.delete
        if self.view.delete:
            response = _("I will remove this node permanently once you select “done”.")
        else:
            response = _("I will no longer remove this node permanently once you select “done”.")

        await context.send(
            embed=await self.cog.pylav.construct_embed(messageable=interaction, description=response),
            ephemeral=True,
        )


class NodeShowEnabledSourcesButton(discord.ui.Button):
    view: NodeManagerMenu

    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.CLOUD_SERVER,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        context = await self.cog.bot.get_context(interaction)
        if self.view.author.id != interaction.user.id:
            return await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
        await context.send(
            embed=await self.cog.pylav.construct_embed(
                messageable=interaction,
                description="__{title}__:\n{sources}".format(
                    title=_("Enabled sources"), sources="\n".join(map(str.title, self.view.source.target.capabilities))
                ),
            ),
            ephemeral=True,
        )
