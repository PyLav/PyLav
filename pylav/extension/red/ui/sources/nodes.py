from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

import discord
import humanize
from redbot.core import i18n
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box, humanize_number
from redbot.vendored.discord.ext import menus
from tabulate import tabulate

from pylav.extension.red.ui.selectors.options.nodes import NodeOption
from pylav.helpers.format.ascii import EightBitANSI
from pylav.logging import getLogger
from pylav.nodes.node import Node
from pylav.type_hints.bot import DISCORD_COG_TYPE

if TYPE_CHECKING:
    from pylav.extension.red.ui.menus.nodes import NodeManagerMenu, NodePickerMenu


LOGGER = getLogger("PyLav.ext.red.ui.sources.node")
_ = Translator("PyLav", Path(__file__))


class NodePickerSource(menus.ListPageSource):
    def __init__(self, guild_id: int, cog: DISCORD_COG_TYPE, pages: list[Node], message_str: str):
        super().__init__(entries=pages, per_page=5)
        self.message_str = message_str
        self.per_page = 5
        self.guild_id = guild_id
        self.select_options: list[NodeOption] = []
        self.cog = cog
        self.select_mapping: dict[str, Node] = {}

    def get_starting_index_and_page_number(self, menu: NodePickerMenu) -> tuple[int, int]:
        page_num = menu.current_page
        start = page_num * self.per_page
        return start, page_num

    async def format_page(self, menu: NodePickerMenu, nodes: list[Node]) -> discord.Embed | str:
        idx_start, page_num = self.get_starting_index_and_page_number(menu)
        page = await self.cog.pylav.construct_embed(messageable=menu.ctx, title=self.message_str)

        total_number_of_entries = len(self.entries)
        current_page = humanize_number(page_num + 1)
        total_number_of_pages = humanize_number(self.get_max_pages())

        match total_number_of_entries:
            case 1:
                message = _("Page 1 / 1 | 1 entry")
            case 0:
                message = _("Page 1 / 1 | 0 entries")
            case __:
                message = _(
                    "Page {current_page_variable_do_not_translate} / {total_number_of_pages_variable_do_not_translate} | {total_number_of_entries_variable_do_not_translate} entries"
                ).format(
                    current_page_variable_do_not_translate=current_page,
                    total_number_of_pages_variable_do_not_translate=total_number_of_pages,
                    total_number_of_entries_variable_do_not_translate=humanize_number(total_number_of_entries),
                )
        page.set_footer(text=message)
        return page

    async def get_page(self, page_number):
        if page_number > self.get_max_pages():
            page_number = 0
        base = page_number * self.per_page
        self.select_options.clear()
        self.select_mapping.clear()
        for i, node in enumerate(self.entries[base : base + self.per_page], start=base):  # noqa: E203
            self.select_options.append(await NodeOption.from_node(node=node, index=i))
            self.select_mapping[f"{node.id}"] = node
        return self.entries[base : base + self.per_page]  # noqa: E203

    def get_max_pages(self):
        """:class:`int`: The maximum number of pages required to paginate this sequence"""
        return self._max_pages or 1


class NodeListSource(menus.ListPageSource):
    def __init__(self, cog: DISCORD_COG_TYPE, pages: list[Node]):
        super().__init__(entries=pages, per_page=1)
        self.cog = cog

    def get_starting_index_and_page_number(self, menu: NodeManagerMenu) -> tuple[int, int]:
        page_num = menu.current_page
        start = page_num * self.per_page
        return start, page_num

    async def format_page(
        self, menu: NodeManagerMenu, node: Node
    ) -> discord.Embed | str:  # sourcery skip: low-code-quality
        locale = f"{i18n.get_babel_locale()}"
        with contextlib.suppress(Exception):
            humanize.i18n.activate(locale)
        idx_start, page_num = self.get_starting_index_and_page_number(menu)
        region = node.region
        coord = node.coordinates
        host = node.host
        port = node.port
        password = node.password
        no = EightBitANSI.paint_red(_("No"))
        yes = EightBitANSI.paint_green(_("Yes"))

        secure = yes if node.ssl else no
        connected = yes if node.available else no
        search_only = yes if node.search_only else no

        node_stats = await node.fetch_stats()
        pylav_connected_players = len(node.connected_players)
        pylav_active_players = len(node.playing_players)

        if node_stats:
            server_connected_players = node_stats.players
            server_active_players = node_stats.playingPlayers
            if node.stats:
                frames_sent = node.stats.frames_sent
                frames_nulled = node.stats.frames_nulled
                frames_deficit = node.stats.frames_deficit
            else:
                frames_sent = 0
                frames_nulled = 0
                frames_deficit = 0
            uptime = humanize.naturaldelta(node_stats.uptime_seconds)
            system_load = humanize_number(round(node_stats.cpu.systemLoad, 2))
            lavalink_load = humanize_number(round(node_stats.cpu.lavalinkLoad, 2))
            free = humanize.naturalsize(node_stats.memory.free, binary=True)
            used = humanize.naturalsize(node_stats.memory.used, binary=True)
            allocated = humanize.naturalsize(node_stats.memory.allocated, binary=True)
            reservable = humanize.naturalsize(node_stats.memory.reservable, binary=True)
            penalty = humanize_number(round(node.penalty - 1, 2))
        else:
            server_connected_players = 0
            server_active_players = 0
            frames_sent = 0
            frames_nulled = 0
            frames_deficit = 0
            uptime = "?"
            system_load = "?"
            lavalink_load = "?"
            free = "?"
            used = "?"
            allocated = "?"
            reservable = "?"
            penalty = "?"
        feature_str = "".join(f"{EightBitANSI.paint_blue(feature)}\n" for feature in sorted(node.capabilities))
        feature_str = feature_str.strip() or EightBitANSI.paint_red(_("None / Unknown"))
        humanize.i18n.deactivate()
        t_property = EightBitANSI.paint_yellow(_("Property"), bold=True, underline=True)
        t_values = EightBitANSI.paint_yellow(_("Value"), bold=True, underline=True)
        coordinate_str = EightBitANSI.paint_white(
            _("Latitude: {latitude_variable_do_not_translate}\nLongitude: {longitude_variable_do_not_translate}")
        ).format(
            latitude_variable_do_not_translate=EightBitANSI.paint_blue(coord[0] if coord else "?"),
            longitude_variable_do_not_translate=EightBitANSI.paint_blue(coord[1] if coord else "?"),
        )

        data = {
            EightBitANSI.paint_white(_("Region")): EightBitANSI.paint_blue(region or _("N/A")),
            EightBitANSI.paint_white(_("Coordinates")): coordinate_str,
            EightBitANSI.paint_white(_("Host")): EightBitANSI.paint_blue(host),
            EightBitANSI.paint_white(_("Port")): EightBitANSI.paint_blue(port),
            EightBitANSI.paint_white(_("Password")): EightBitANSI.paint_blue("*" * min([len(password), 10])),
            EightBitANSI.paint_white(_("SSL")): secure,
            EightBitANSI.paint_white(_("Available")): connected,
            EightBitANSI.paint_white(_("Search Only")): search_only,
            EightBitANSI.paint_white(_("Players\nConnected\nActive")): EightBitANSI.paint_blue(
                f"-\n{pylav_connected_players}/{server_connected_players or '?'}\n"
                f"{pylav_active_players}/{server_active_players or '?'}"
            ),
            EightBitANSI.paint_white(_("Frames Lost")): EightBitANSI.paint_blue(
                f"{(abs(frames_deficit) + abs(frames_nulled))/(frames_sent or 1) * 100:.2f}%"
            )
            if ((abs(frames_deficit) + abs(frames_nulled)) / (frames_sent or 1)) > 0
            else EightBitANSI.paint_blue("0%"),
            EightBitANSI.paint_white(_("Uptime")): EightBitANSI.paint_blue(uptime),
            EightBitANSI.paint_white(_("CPU Load\nLavalink\nSystem")): EightBitANSI.paint_blue(
                f"-\n{lavalink_load}%\n{system_load}%"
            ),
            EightBitANSI.paint_white(_("Penalty")): EightBitANSI.paint_blue(penalty),
            EightBitANSI.paint_white(_("Memory\nUsed\nFree\nAllocated\nReservable")): EightBitANSI.paint_blue(
                f"-\n{used}\n{free}\n{allocated}\n{reservable}"
            ),
            EightBitANSI.paint_white(_("Features")): feature_str,
        }
        description = box(
            tabulate([{t_property: k, t_values: v} for k, v in data.items()], headers="keys", tablefmt="fancy_grid"),
            lang="ansi",
        )
        embed = await self.cog.pylav.construct_embed(
            messageable=menu.ctx,
            title=node.name,
            description=description,
        )

        total_number_of_entries = len(self.entries)
        current_page = humanize_number(page_num + 1)
        total_number_of_pages = humanize_number(self.get_max_pages())
        match total_number_of_entries:
            case 1:
                message = _("Page 1 / 1 | 1 node")
            case 0:
                message = _("Page 1 / 1 | 0 nodes")
            case __:
                message = _(
                    "Page {current_page_variable_do_not_translate} / {total_number_of_pages_variable_do_not_translate} | {total_number_of_entries_variable_do_not_translate} nodes"
                ).format(
                    current_page_variable_do_not_translate=current_page,
                    total_number_of_pages_variable_do_not_translate=total_number_of_pages,
                    total_number_of_entries_variable_do_not_translate=humanize_number(total_number_of_entries),
                )

        embed.set_footer(text=message)
        return embed


class NodeManageSource(menus.ListPageSource):
    target: Node | None

    def __init__(self, cog: DISCORD_COG_TYPE):
        self.cog = cog
        self.target = None
        self.per_page = 1

    @property
    def entries(self) -> list[Node]:
        return self.cog.pylav.node_manager.nodes

    @property
    def _max_pages(self) -> int:
        return len(self.entries) or 1

    async def get_page(self, page_number: int) -> Node:
        """Returns either a single element of the sequence or
        a slice of the sequence.

        If :attr:`per_page` is set to ``1`` then this returns a single
        element. Otherwise it returns at most :attr:`per_page` elements.

        Returns
        ---------
        Node
            The data returned.
        """
        self.target = self.entries[page_number]
        return self.target

    def get_starting_index_and_page_number(self, menu: NodeManagerMenu) -> tuple[int, int]:
        page_num = menu.current_page
        start = page_num * self.per_page
        return start, page_num

    async def format_page(
        self, menu: NodeManagerMenu, node: Node
    ) -> discord.Embed | str:  # sourcery skip: low-code-quality
        locale = f"{i18n.get_babel_locale()}"
        with contextlib.suppress(Exception):
            humanize.i18n.activate(locale)
        await menu.prepare()
        idx_start, page_num = self.get_starting_index_and_page_number(menu)
        region = node.region
        coord = node.coordinates
        host = node.host
        port = node.port
        password = node.password
        no = EightBitANSI.paint_red(_("No"))
        yes = EightBitANSI.paint_green(_("Yes"))

        secure = yes if node.ssl else no
        connected = yes if node.available else no
        search_only = yes if node.search_only else no

        node_stats = await node.fetch_stats()
        pylav_connected_players = len(node.connected_players)
        pylav_active_players = len(node.playing_players)

        if node_stats:
            server_connected_players = node_stats.players
            server_active_players = node_stats.playingPlayers
            if node.stats:
                frames_sent = node.stats.frames_sent
                frames_nulled = node.stats.frames_nulled
                frames_deficit = node.stats.frames_deficit
            else:
                frames_sent = 0
                frames_nulled = 0
                frames_deficit = 0
            uptime = humanize.naturaldelta(node_stats.uptime_seconds)
            system_load = humanize_number(round(node_stats.cpu.systemLoad, 2))
            lavalink_load = humanize_number(round(node_stats.cpu.lavalinkLoad, 2))
            free = humanize.naturalsize(node_stats.memory.free, binary=True)
            used = humanize.naturalsize(node_stats.memory.used, binary=True)
            allocated = humanize.naturalsize(node_stats.memory.allocated, binary=True)
            reservable = humanize.naturalsize(node_stats.memory.reservable, binary=True)
            penalty = humanize_number(round(node.penalty - 1, 2))
        else:
            server_connected_players = 0
            server_active_players = 0
            frames_sent = 0
            frames_nulled = 0
            frames_deficit = 0
            uptime = "?"
            system_load = "?"
            lavalink_load = "?"
            free = "?"
            used = "?"
            allocated = "?"
            reservable = "?"
            penalty = "?"
        feature_str = "".join(f"{EightBitANSI.paint_blue(feature)}\n" for feature in sorted(node.capabilities))
        feature_str = feature_str.strip() or EightBitANSI.paint_red(_("None / Unknown"))
        humanize.i18n.deactivate()
        t_property = EightBitANSI.paint_yellow(_("Property"), bold=True, underline=True)
        t_values = EightBitANSI.paint_yellow(_("Value"), bold=True, underline=True)
        coordinate_str = EightBitANSI.paint_white(
            _("Latitude: {latitude_variable_do_not_translate}\nLongitude: {longitude_variable_do_not_translate}")
        ).format(
            latitude_variable_do_not_translate=EightBitANSI.paint_blue(coord[0] if coord else "?"),
            longitude_variable_do_not_translate=EightBitANSI.paint_blue(coord[1] if coord else "?"),
        )

        data = {
            EightBitANSI.paint_white(_("Region")): EightBitANSI.paint_blue(region or _("N/A")),
            EightBitANSI.paint_white(_("Coordinates")): coordinate_str,
            EightBitANSI.paint_white(_("Host")): EightBitANSI.paint_blue(host),
            EightBitANSI.paint_white(_("Port")): EightBitANSI.paint_blue(port),
            EightBitANSI.paint_white(_("Password")): EightBitANSI.paint_blue("*" * min([len(password), 10])),
            EightBitANSI.paint_white(_("SSL")): secure,
            EightBitANSI.paint_white(_("Available")): connected,
            EightBitANSI.paint_white(_("Search Only")): search_only,
            EightBitANSI.paint_white(_("Players\nConnected\nActive")): EightBitANSI.paint_blue(
                f"-\n{pylav_connected_players}/{server_connected_players or '?'}\n"
                f"{pylav_active_players}/{server_active_players or '?'}"
            ),
            EightBitANSI.paint_white(_("Frames Lost")): EightBitANSI.paint_blue(
                f"{(abs(frames_deficit) + abs(frames_nulled)) / (frames_sent or 1) * 100:.2f}%"
            )
            if ((abs(frames_deficit) + abs(frames_nulled)) / (frames_sent or 1)) > 0
            else EightBitANSI.paint_blue("0%"),
            EightBitANSI.paint_white(_("Uptime")): EightBitANSI.paint_blue(uptime),
            EightBitANSI.paint_white(_("CPU Load\nLavalink\nSystem")): EightBitANSI.paint_blue(
                f"-\n{lavalink_load}%\n{system_load}%"
            ),
            EightBitANSI.paint_white(_("Penalty")): EightBitANSI.paint_blue(penalty),
            EightBitANSI.paint_white(_("Memory\nUsed\nFree\nAllocated\nReservable")): EightBitANSI.paint_blue(
                f"-\n{used}\n{free}\n{allocated}\n{reservable}"
            ),
            EightBitANSI.paint_white(_("Features")): feature_str,
        }
        description = box(
            tabulate([{t_property: k, t_values: v} for k, v in data.items()], headers="keys", tablefmt="fancy_grid"),
            lang="ansi",
        )
        embed = await self.cog.pylav.construct_embed(
            messageable=menu.ctx,
            title=node.name,
            description=description,
        )

        number_of_pages = self.get_max_pages()
        total_number_of_entries = len(self.entries)
        current_page = humanize_number(page_num + 1)
        total_number_of_pages = humanize_number(self.get_max_pages())
        match number_of_pages:
            case 1:
                message = _("Page 1 / 1 | 1 node")
            case 0:
                message = _("Page 1 / 1 | 0 nodes")
            case __:
                message = _(
                    "Page {current_page_variable_do_not_translate} / {total_number_of_pages_variable_do_not_translate} | {total_number_of_entries_variable_do_not_translate} nodes"
                ).format(
                    current_page_variable_do_not_translate=current_page,
                    total_number_of_pages_variable_do_not_translate=total_number_of_pages,
                    total_number_of_entries_variable_do_not_translate=total_number_of_entries,
                )

        embed.set_footer(text=message)
        return embed
