from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from discord.app_commands import Choice, Transformer
from discord.ext import commands

from pylav.types import ContextT, InteractionT

if TYPE_CHECKING:
    from pylav.sql.models import PlaylistModel

    PlaylistConverter = TypeVar("PlaylistConverter", bound=list[PlaylistModel])
else:

    class PlaylistConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[PlaylistModel]:
            """Converts a playlist name or ID to a list of matching objects."""
            from pylav import EntryNotFoundError

            try:
                playlists = await ctx.lavalink.playlist_db_manager.get_playlist_by_name_or_id(arg)
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Playlist with name or id `{arg}` not found.") from e
            return playlists

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[PlaylistModel]:
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            return [
                Choice(name=p.name, value=f"{p.id}")
                for p in await interaction.client.lavalink.playlist_db_manager.get_playlist_by_name(current, limit=25)
                if current.lower() in p.name.lower()
            ]
