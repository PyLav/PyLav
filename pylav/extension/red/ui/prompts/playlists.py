from __future__ import annotations

from pathlib import Path

from redbot.core.i18n import Translator

from pylav.core.context import PyLavContext
from pylav.extension.red.ui.menus.playlist import PlaylistPickerMenu
from pylav.extension.red.ui.selectors.playlist import PlaylistSelectSelector
from pylav.extension.red.ui.sources.playlist import PlaylistPickerSource
from pylav.helpers.format.strings import shorten_string
from pylav.storage.models.playlist import Playlist
from pylav.type_hints.bot import DISCORD_COG_TYPE

_ = Translator("PyLav", Path(__file__))


async def maybe_prompt_for_playlist(
    cog: DISCORD_COG_TYPE, context: PyLavContext, playlists: list[Playlist]
) -> Playlist | None:
    if len(playlists) > 1:
        playlist_picker = PlaylistPickerMenu(
            cog=cog,
            bot=cog.bot,
            source=PlaylistPickerSource(
                guild_id=context.guild.id,
                cog=cog,
                pages=playlists,
                message_str=shorten_string(
                    max_length=100, string=_("Multiple playlists matched. Pick the one which you meant.")
                ),
            ),
            selector_cls=PlaylistSelectSelector,
            delete_after_timeout=True,
            clear_buttons_after=True,
            starting_page=0,
            selector_text=shorten_string(max_length=100, string=_("Pick a playlist.")),
            original_author=context.interaction.user if context.interaction else context.author,
        )

        await playlist_picker.start(context)
        try:
            await playlist_picker.wait_for_response()
            playlist = playlist_picker.result
        except TimeoutError:
            playlist = None
    else:
        playlist = playlists[0]

    return playlist
