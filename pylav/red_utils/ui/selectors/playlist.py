from __future__ import annotations

import asyncio
from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav.red_utils.ui.selectors.options.playlist import PlaylistOption
from pylav.sql.models import PlaylistModel
from pylav.types import CogT, InteractionT

_ = Translator("PyLavShared", Path(__file__))


class PlaylistSelectSelector(discord.ui.Select):
    def __init__(
        self,
        options: list[PlaylistOption],
        cog: CogT,
        placeholder: str,
        mapping: dict[str, PlaylistModel],
    ):
        super().__init__(min_values=1, max_values=1, options=options, placeholder=placeholder)
        self.cog = cog
        self.mapping = mapping
        self.playlist: PlaylistModel = None  # type:ignore
        self.responded = asyncio.Event()

    async def callback(self, interaction: InteractionT):
        playlist_id = self.values[0]
        self.playlist: PlaylistModel = self.mapping.get(playlist_id)
        if self.playlist is None:
            await interaction.response.send_message(
                embed=await self.cog.lavalink.construct_embed(messageable=interaction, title=_("Playlist not found")),
                ephemeral=True,
            )
            self.view.stop()
            await self.view.on_timeout()
            return
        self.responded.set()
        self.view.stop()
        await self.view.on_timeout()


class PlaylistPlaySelector(discord.ui.Select):
    def __init__(
        self,
        options: list[PlaylistOption],
        cog: CogT,
        placeholder: str,
        mapping: dict[str, PlaylistModel],
    ):
        super().__init__(min_values=1, max_values=1, options=options, placeholder=placeholder)
        self.cog = cog
        self.mapping = mapping

    async def callback(self, interaction: InteractionT):
        if self.view.author.id != interaction.user.id:
            await interaction.response.send_message(
                embed=await self.cog.lavalink.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option")
                ),
                ephemeral=True,
            )
            return
        playlist_id = self.values[0]
        playlist: PlaylistModel = self.mapping.get(playlist_id)
        if playlist is None:
            await interaction.response.send_message(
                embed=await self.cog.lavalink.construct_embed(messageable=interaction, title=_("Playlist not found")),
                ephemeral=True,
            )
            self.view.stop()
            await self.view.on_timeout()
            return
        await self.cog.command_playlist_play.callback(self.cog, interaction, playlist=[playlist])
        self.view.stop()
        await self.view.on_timeout()
