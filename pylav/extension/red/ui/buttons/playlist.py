from __future__ import annotations

import itertools
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import discord
from discord import Emoji, PartialEmoji
from redbot.core.i18n import Translator

from pylav.extension.red.utils import rgetattr
from pylav.helpers import emojis
from pylav.helpers.format.strings import shorten_string
from pylav.storage.models.playlist import Playlist
from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

if TYPE_CHECKING:
    from pylav.extension.red.ui.menus.playlist import PlaylistCreationFlow, PlaylistManageFlow
_ = Translator("PyLav", Path(__file__))


class PlaylistDeleteButton(discord.ui.Button):
    view: PlaylistManageFlow

    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.TRASH,
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
        self.view.cancelled = False
        self.view.delete = not self.view.delete
        if self.view.delete:
            response = _("I will delete this playlist permanently once you select “done”.")
        else:
            response = _("I will no longer delete this playlist permanently once you select “done”.")

        await context.send(
            embed=await self.cog.pylav.construct_embed(messageable=interaction, description=response),
            ephemeral=True,
        )


class PlaylistClearButton(discord.ui.Button):
    view: PlaylistManageFlow

    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.CLEAR,
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
        self.view.cancelled = False
        self.view.clear = not self.view.clear
        if self.view.clear:
            response = _("I will remove all tracks from this playlist.")
        else:
            response = _("I will no longer remove all tracks from this playlist.")

        await context.send(
            embed=await self.cog.pylav.construct_embed(messageable=interaction, description=response),
            ephemeral=True,
        )


class PlaylistDownloadButton(discord.ui.Button):
    view: PlaylistManageFlow

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
            await interaction.response.defer(ephemeral=True, thinking=True)
        context = await self.cog.bot.get_context(interaction)
        if self.view.author.id != interaction.user.id:
            return await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
        async with self.view.playlist.to_yaml(guild=interaction.guild) as (yaml_file, compressed):
            yaml_file: BytesIO
            if compressed == "gzip":
                message = _(
                    "Here is your playlist: {playlist_name_variable_do_not_translate}. "
                    "This file is compressed using Gzip to make it possible to be sent via Discord. "
                    "You can use {url_name_variable_do_not_translate} to decompress it."
                ).format(
                    playlist_name_variable_do_not_translate=await self.view.playlist.get_name_formatted(with_url=True),
                    url_name_variable_do_not_translate="<https://gzip.swimburger.net/>",
                )
            elif compressed == "brotli":
                message = _(
                    "Here is your playlist: {playlist_name_name_variable_do_not_translate}. "
                    "This file is compressed using Brotli to make it possible to be sent via Discord."
                ).format(
                    playlist_name_name_variable_do_not_translate=await self.view.playlist.get_name_formatted(
                        with_url=True
                    )
                )
            else:
                message = _("Here is your playlist: {playlist_name_name_variable_do_not_translate}.").format(
                    playlist_name_name_variable_do_not_translate=await self.view.playlist.get_name_formatted(
                        with_url=True
                    )
                )

            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction,
                    description=message,
                ),
                file=discord.File(
                    filename=f"{await self.view.playlist.fetch_name()}{'.gz' if compressed=='gzip' else '.br' if compressed=='brotli' else ''}.pylav",
                    fp=yaml_file,
                ),
                ephemeral=True,
            )


class PlaylistUpdateButton(discord.ui.Button):
    view: PlaylistManageFlow

    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.UPDATE,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=True)
        context = await self.cog.bot.get_context(interaction)
        if self.view.author.id != interaction.user.id:
            return await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("You are not authorized to interact with this option.")
                ),
                ephemeral=True,
            )
        self.view.cancelled = False
        self.view.update = not self.view.update
        if (await self.view.playlist.fetch_url() or self.view.url) and self.view.update:
            response = _("I will update this playlist with the latest tracks, press done to continue.")
        else:
            self.view.update = False
            response = _("I will no longer update this playlist with the latest tracks.")
        await context.send(
            embed=await self.cog.pylav.construct_embed(messageable=interaction, description=response),
            ephemeral=True,
        )


class PlaylistInfoButton(discord.ui.Button):
    view: PlaylistManageFlow

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        style: discord.ButtonStyle,
        emoji: str | Emoji | PartialEmoji,
        playlist: Playlist,
        row: int = None,
    ):
        super().__init__(
            style=style,
            emoji=emoji,
            row=row,
        )
        self.cog = cog
        self.playlist = playlist

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

        from pylav.extension.red.ui.menus.generic import PaginatingMenu
        from pylav.extension.red.ui.sources.playlist import TrackMappingSource

        tracks = await self.view.playlist.fetch_tracks()
        await PaginatingMenu(
            bot=self.cog.bot,
            cog=self.cog,
            source=TrackMappingSource(
                guild_id=interaction.guild.id,
                cog=self.cog,
                author=interaction.user,
                entries=tracks,
                playlist=self.playlist,
            ),
            delete_after_timeout=True,
            starting_page=0,
            original_author=interaction.user,
        ).start(context)


class PlaylistQueueButton(discord.ui.Button):
    view: PlaylistManageFlow

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
        self.view.queue = not self.view.queue
        if self.view.queue:
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("I will add the current queue this playlist.")
                ),
                ephemeral=True,
            )
        else:
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("I will no longer add the current queue to this playlist.")
                ),
                ephemeral=True,
            )


class PlaylistDedupeButton(discord.ui.Button):
    view: PlaylistManageFlow

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
        self.view.dedupe = not self.view.dedupe
        if self.view.dedupe:
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("I will remove all duplicate tracks from the queue.")
                ),
                ephemeral=True,
            )
        else:
            await context.send(
                embed=await self.cog.pylav.construct_embed(
                    messageable=interaction, description=_("I will no longer remove duplicate tracks from the queue.")
                ),
                ephemeral=True,
            )


class PlaylistUpsertButton(discord.ui.Button):
    view: PlaylistCreationFlow | PlaylistManageFlow

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        style: discord.ButtonStyle,
        op: Literal["url", "name", "scope", "add", "remove"],
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
        if self.op == "url":
            await self.view.prompt_url(interaction)
        elif self.op == "name":
            await self.view.prompt_name(interaction)
        elif self.op == "scope":
            await self.view.prompt_scope(interaction)
        elif self.op == "add":
            await self.view.prompt_add_tracks(interaction)
        elif self.op == "remove":
            await self.view.prompt_remove_tracks(interaction)


class EnqueuePlaylistButton(discord.ui.Button):
    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        style: discord.ButtonStyle,
        row: int = None,
        emoji: Emoji | PartialEmoji = emojis.PLAYLIST,
        playlist: Playlist = None,
    ):
        self.cog = cog
        super().__init__(
            style=style,
            emoji=emoji,
            row=row,
        )
        self.playlist = playlist

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        context = await self.cog.bot.get_context(interaction)
        if not self.playlist:
            playlists = await self.cog.pylav.playlist_db_manager.get_all_for_user(
                requester=context.author.id,
                vc=rgetattr(context.author, "voice.channel", None),
                guild=context.guild,
                channel=context.channel,
            )
            playlists = list(itertools.chain.from_iterable(playlists))

            from pylav.extension.red.ui.menus.playlist import PlaylistPickerMenu
            from pylav.extension.red.ui.selectors.playlist import PlaylistPlaySelector
            from pylav.extension.red.ui.sources.playlist import PlaylistPickerSource

            await PlaylistPickerMenu(
                cog=self.cog,
                bot=self.cog.bot,
                selector_cls=PlaylistPlaySelector,
                source=PlaylistPickerSource(
                    guild_id=context.guild.id,
                    cog=self.cog,
                    pages=playlists,
                    message_str=_("Playlists you can currently play."),
                ),
                delete_after_timeout=True,
                clear_buttons_after=True,
                starting_page=0,
                original_author=context.author,
                selector_text=shorten_string(max_length=100, string=_("Pick a playlist.")),
            ).start(context)
        else:
            await self.cog.command_playlist_play.callback(self.cog, interaction, playlist=[self.playlist])
        if hasattr(self.view, "prepare"):
            await self.view.prepare()
            kwargs = await self.view.get_page(self.view.current_page)
            attachments = []
            if "file" in kwargs:
                attachments = [kwargs.pop("file")]
            elif "files" in kwargs:
                attachments = kwargs.pop("files")
            if attachments:
                kwargs["attachments"] = attachments
            await self.view.message.edit(view=self.view, **kwargs)


class SaveQueuePlaylistButton(discord.ui.Button):
    def __init__(self, cog: DISCORD_COG_TYPE, style: discord.ButtonStyle, row: int = None):
        super().__init__(
            style=style,
            emoji=emojis.QUEUE,
            row=row,
        )
        self.cog = cog

    async def callback(self, interaction: DISCORD_INTERACTION_TYPE):
        from pylav.extension.red.ui.modals.playlist import PlaylistSaveModal

        modal = PlaylistSaveModal(self.cog, self, _("What should the playlist name be?"))
        await interaction.response.send_modal(modal)
