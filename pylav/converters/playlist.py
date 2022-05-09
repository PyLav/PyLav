from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from discord.ext import commands

from pylav.types import ContextT

if TYPE_CHECKING:
    from pylav.sql.models import PlaylistModel

    PlaylistConverter = TypeVar("PlaylistConverter", bound=list[PlaylistModel])
else:

    class PlaylistConverter(commands.Converter):
        async def convert(self, ctx: ContextT, arg: str) -> list[PlaylistModel]:
            """Converts a playlist name or ID to a list of matching objects."""
            from pylav import EntryNotFoundError

            try:
                playlists = await ctx.lavalink.playlist_db_manager.get_playlist_by_name_or_id(arg)
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Playlist with name or id `{arg}` not found.") from e

            return playlists
