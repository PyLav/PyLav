from __future__ import annotations

from pathlib import Path

import discord
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_number
from redbot.vendored.discord.ext import menus

from pylav.extension.red.ui.menus.generic import BaseMenu
from pylav.extension.red.utils import rgetattr
from pylav.logging import getLogger
from pylav.players.player import Player
from pylav.type_hints.bot import DISCORD_COG_TYPE

LOGGER = getLogger("PyLav.ext.red.ui.sources.player")
_ = Translator("PyLav", Path(__file__))


class PlayersSource(menus.ListPageSource):
    def __init__(self, cog: DISCORD_COG_TYPE, specified_guild: int = None):
        super().__init__([], per_page=1)
        self.cog = cog
        self.current_player = None
        self.specified_guild = specified_guild

    @property
    def entries(self) -> list[Player]:
        if self.specified_guild is not None and (player := self.cog.pylav.player_manager.get(self.specified_guild)):
            return [player]
        return self.cog.pylav.player_manager.connected_players

    @entries.setter
    def entries(self, players: list[Player]):
        pass

    def get_max_pages(self):
        if self.specified_guild is not None and (player := self.cog.pylav.player_manager.get(self.specified_guild)):
            players = [player]
        else:
            players = self.cog.pylav.player_manager.connected_players
        pages, left_over = divmod(len(players), self.per_page)
        if left_over:
            pages += 1
        return pages or 1

    def get_starting_index_and_page_number(self, menu: BaseMenu) -> tuple[int, int]:
        page_num = menu.current_page
        start = page_num * self.per_page
        return start, page_num

    async def format_page(self, menu: BaseMenu, player: Player) -> discord.Embed:
        idx_start, page_num = self.get_starting_index_and_page_number(menu)
        connect_dur = discord.utils.format_dt(player.connected_at, style="R")
        self.current_player = player
        guild_name = player.guild.name
        queue_len = player.queue.size()
        history_queue_len = player.history.size()
        server_owner = f"{player.guild.owner} ({player.guild.owner.id})"
        current_track = (
            await player.current.get_track_display_name(max_length=50, with_url=True)
            if player.current
            else _("I am not currently playing anything on this server.")
        )

        listener_count = sum(True for m in iter(rgetattr(player, "channel.members", [])) if not m.bot)
        listeners = humanize_number(listener_count)
        current_track += "\n"

        match queue_len:
            case 1:
                queue_length_translation = _("1 track")
            case 0:
                queue_length_translation = _("0 tracks")
            case __:
                queue_length_translation = _("{queue_length_variable_do_not_translate} tracks").format(
                    queue_length_variable_do_not_translate=humanize_number(queue_len)
                )

        match history_queue_len:
            case 1:
                history_queue_length_translation = _("1 track")
            case 0:
                history_queue_length_translation = _("0 tracks")
            case __:
                history_queue_length_translation = _("{history_queue_length_variable_do_not_translate} tracks").format(
                    history_queue_length_variable_do_not_translate=humanize_number(history_queue_len)
                )

        field_values = "\n".join(
            f"**{i[0]}**: {i[1]}"
            for i in [
                (_("Server Owner"), server_owner),
                (_("Connected"), connect_dur),
                (_("Users in Voice Channel"), listeners),
                (
                    _("Queue Length"),
                    queue_length_translation,
                ),
                (
                    _("Queue History Length"),
                    history_queue_length_translation,
                ),
            ]
        )

        current_track += field_values

        embed = await self.cog.pylav.construct_embed(messageable=menu.ctx, title=guild_name, description=current_track)

        total_number_of_entries = len(self.entries)
        current_page = humanize_number(page_num + 1)
        total_number_of_pages = humanize_number(self.get_max_pages())

        match total_number_of_entries:
            case 1:
                message = _("Page 1 / 1 | 1 server")
            case 0:
                message = _("Page 1 / 1 | 0 servers")
            case __:
                message = _(
                    "Page {current_page_variable_do_not_translate} / {total_number_of_pages_variable_do_not_translate} | {total_number_of_entries_variable_do_not_translate} servers"
                ).format(
                    current_page_variable_do_not_translate=current_page,
                    total_number_of_pages_variable_do_not_translate=total_number_of_pages,
                    total_number_of_entries_variable_do_not_translate=humanize_number(total_number_of_entries),
                )

        embed.set_footer(text=message)
        return embed
