from __future__ import annotations

import asyncio
from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav.extension.red.ui.selectors.options.playlist import PlaylistOption
from pylav.helpers.format.strings import shorten_string
from pylav.storage.models.playlist import Playlist
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

_ = Translator("PyLav", Path(__file__))


class PlaylistSelectSelector(discord.ui.Select):
    def __init__(
        self,
        options: list[PlaylistOption],
        cog: DISCORD_COG_TYPE,
        placeholder: str,
        mapping: dict[str, Playlist],
    ):
        super().__init__(
            min_values=1,
            max_values=1,
            options=options,
            placeholder=shorten_string(max_length=100, string=placeholder),
        )
        self.cog = cog
        self.mapping = mapping
        self.playlist: Playlist | None = None
        self.responded = asyncio.Event()

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        playlist_id = self.values[0]
        self.playlist: Playlist = self.mapping.get(playlist_id)
        if self.playlist is None:
            await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(messageable=interaction, title=_("Playlist was not found.")),
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
        cog: DISCORD_COG_TYPE,
        placeholder: str,
        mapping: dict[str, Playlist],
    ):
        super().__init__(
            min_values=1,
            max_values=1,
            options=options,
            placeholder=shorten_string(max_length=100, string=placeholder),
        )
        self.cog = cog
        self.mapping = mapping

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if self.view.author.id != interaction.user.id:
            await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
            return
        playlist_id = self.values[0]
        playlist: Playlist = self.mapping.get(playlist_id)
        if playlist is None:
            await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(messageable=interaction, title=_("Playlist was not found.")),
                ephemeral=True,
            )
            self.view.stop()
            await self.view.on_timeout()
            return
        await self.cog.command_playlist_play.callback(self.cog, interaction, playlist=[playlist])
        self.view.stop()
        await self.view.on_timeout()
