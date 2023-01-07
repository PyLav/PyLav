from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Literal

import discord
from redbot.core.i18n import Translator

from pylav.helpers import emojis
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE
from pylav.utils.vendor.redbot import AsyncIter

_ = Translator("PyLav", Path(__file__))


class DisconnectButton(discord.ui.Button):
    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        style: discord.ButtonStyle,
        row: int = None,
    ):
        super().__init__(
            style=style,
            emoji=emojis.POWER,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        context = await self.cog.bot.get_context(interaction)
        if not await self.view.bot.is_owner(context.author):
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=context, title=_("You are not authorized to perform this action")
                ),
                ephemeral=True,
            )
            return
        player = self.view.source.current_player
        if not player:
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=context, title=_("No Player Available For Action - Try Refreshing")
                ),
                ephemeral=True,
            )
            return
        if notify_channel := await player.notify_channel():
            with contextlib.suppress(discord.HTTPException):
                await notify_channel.send(
                    embed=await self.cog.pylav.construct_embed(
                        title=_("Bot Owner Action"), description=_("Player disconnected")
                    )
                )
        await player.disconnect(requester=context.author)

        await self.view.prepare()
        kwargs = await self.view.get_page(self.view.current_page)
        await self.view.message.edit(view=self.view, **kwargs)


class StopTrackButton(discord.ui.Button):
    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        style: discord.ButtonStyle,
        row: int = None,
    ):
        super().__init__(
            style=style,
            emoji=emojis.STOP,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        context = await self.cog.bot.get_context(interaction)
        if not await self.view.bot.is_owner(context.author):
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=context, description=_("You are not authorized to perform this action")
                ),
                ephemeral=True,
            )
            return
        player = self.view.source.current_player
        if not player:
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=context, description=_("No Player Available For Action - Try Refreshing")
                ),
                ephemeral=True,
            )
            return

        await player.stop(interaction.user)
        if notify_channel := await player.notify_channel():
            with contextlib.suppress(discord.HTTPException):
                await notify_channel.send(
                    embed=await self.cog.pylav.construct_embed(
                        title=_("Bot Owner Action"), description=_("Player stopped")
                    )
                )

        await self.view.prepare()
        kwargs = await self.view.get_page(self.view.current_page)
        await self.view.message.edit(view=self.view, **kwargs)


class DisconnectAllButton(discord.ui.Button):
    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        disconnect_type: Literal["all", "inactive"],
        style: discord.ButtonStyle,
        row: int = None,
    ):
        super().__init__(
            style=style,
            emoji=emojis.POWER,
            row=row,
        )

        self.disconnect_type = disconnect_type
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        context = await self.cog.bot.get_context(interaction)
        if not await self.view.bot.is_owner(context.author):
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=context, description=_("You are not authorized to perform this action")
                ),
                ephemeral=True,
            )
            return

        players = (
            self.cog.pylav.player_manager.connected_players
            if self.disconnect_type == "all"
            else self.cog.pylav.player_manager.not_playing_players
        )
        if not players:
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=context, description=_("No Players Available For Action - Try Refreshing")
                ),
                ephemeral=True,
            )
            return
        async for player in AsyncIter(players):
            if notify_channel := await player.notify_channel():
                with contextlib.suppress(discord.HTTPException):
                    await notify_channel.send(
                        embed=await self.cog.pylav.construct_embed(
                            title=_("Bot Owner Action"), description=_("Player disconnected")
                        )
                    )
            await player.disconnect(requester=context.author)

        await self.view.prepare()
        kwargs = await self.view.get_page(self.view.current_page)
        await self.view.message.edit(view=self.view, **kwargs)
