from __future__ import annotations

from pathlib import Path
from typing import Literal

import discord
from redbot.core.i18n import Translator

from pylav.extension.red.ui.selectors.options.queue import QueueTrackOption, SearchTrackOption
from pylav.helpers.format.strings import shorten_string
from pylav.players.tracks.obj import Track
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

_ = Translator("PyLav", Path(__file__))


class QueueSelectTrack(discord.ui.Select):
    def __init__(
        self,
        options: list[QueueTrackOption],
        cog: DISCORD_COG_TYPE,
        placeholder: str,
        interaction_type: Literal["remove", "play"],
        mapping: dict[str, Track],
    ):
        super().__init__(
            min_values=1,
            max_values=1,
            options=options,
            placeholder=shorten_string(max_length=100, string=placeholder),
        )
        self.cog = cog
        self.interaction_type = interaction_type
        self.mapping = mapping

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        track_id = self.values[0]
        track: Track = self.mapping.get(track_id)
        if track is None:
            await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(description="Track not found", messageable=interaction),
                ephemeral=True,
            )
            self.view.stop()
            await self.view.on_timeout()
            return
        player = self.cog.pylav.get_player(interaction.guild)
        if not player:
            await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(
                    description="Player has been disconnected", messageable=interaction
                ),
                ephemeral=True,
            )
            self.view.stop()
            await self.view.on_timeout()
            return

        await interaction.response.defer(ephemeral=True)

        index = player.queue.index(track)
        index += 1
        if self.interaction_type == "remove":
            await self.cog.command_remove.callback(
                self.cog, interaction, track_url_or_index=f"{index}", remove_duplicates=True
            )
        else:
            await self.cog.command_bump.callback(self.cog, interaction, queue_number=index)
        self.view.stop()
        await self.view.on_timeout()


class SearchSelectTrack(discord.ui.Select):
    def __init__(
        self,
        options: list[SearchTrackOption],
        cog: DISCORD_COG_TYPE,
        placeholder: str,
        mapping: dict[str, Track],
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
        track_id = self.values[0]
        track: Track = self.mapping.get(track_id)

        if track is None:
            await interaction.response.send_message(
                embed=await self.cog.pylav.construct_embed(messageable=interaction, title=_("Track was not found.")),
                ephemeral=True,
            )
            self.view.stop()
            await self.view.on_timeout()
            return

        await self.cog.command_play.callback(
            self.cog,
            interaction,
            query=[track.uri],
        )
        self.view.stop()
        await self.view.on_timeout()
