from __future__ import annotations

import asyncio
import contextlib
import pathlib
from collections.abc import Iterator
from typing import TYPE_CHECKING

import asyncpg
import discord

from pylav.constants.config import ENABLE_NODE_RESUMING
from pylav.events.player import PlayerConnectedEvent
from pylav.exceptions.node import NoNodeAvailableException
from pylav.helpers.format.strings import shorten_string
from pylav.logging import getLogger
from pylav.nodes.node import Node
from pylav.players.player import Player
from pylav.players.query.obj import Query
from pylav.storage.models.player.config import PlayerConfig
from pylav.storage.models.player.state import PlayerState

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLav", pathlib.Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


if TYPE_CHECKING:
    from pylav.core.client import Client

LOGGER = getLogger("PyLav.PlayerManager")


class PlayerController:
    """Represents the player manager that contains all the players.

    len(x):
        Returns the total amount of cached players.
    iter(x):
        Returns an iterator of all the players cached.

    Attributes
    ----------
    default_player_class: :class:`BasePlayer`
        The player that the player manager is initialized with.
    bot: :class:`discord.Client`
        The client that the player manager is initialized with.
    client: :class:`Client`
        The client that the player manager is initialized with.
    """

    __slots__ = ("_players", "default_player_class", "bot", "client", "_global_player_config")

    _global_player_config: PlayerConfig

    def __init__(self, lavalink: Client, player: type[Player] = Player):
        if not issubclass(player, Player):
            raise ValueError("Player must implement Player")

        self.client = lavalink
        self.bot = lavalink.bot
        self._players: dict[int, Player] = {}
        self.default_player_class = player

    def __len__(self):
        return len(self._players)

    def __iter__(self) -> Iterator[tuple[int, Player]]:
        """Returns an iterator that yields a tuple of (guild_id, player)"""
        yield from self.players.items()

    @property
    def players(self) -> dict[int, Player]:
        """Returns a dictionary of all players in manager."""
        return self._players

    @property
    def global_config(self) -> PlayerConfig:
        return self._global_player_config

    @property
    def connected_players(self) -> list[Player]:
        """Returns a list of all the connected players"""
        return [p for p in self.players.values() if p.is_connected]

    @property
    def playing_players(self) -> list[Player]:
        """Returns a list of all the playing players"""
        return [p for p in self.players.values() if p.is_active]

    @property
    def not_playing_players(self) -> list[Player]:
        """Returns a list of all the not playing players"""
        return [p for p in self.players.values() if not p.is_active]

    @property
    def paused_players(self) -> list[Player]:
        """Returns a list of all the paused players"""
        return [p for p in self.players.values() if p.paused]

    @property
    def empty_players(self) -> list[Player]:
        """Returns a list of all the empty players"""
        return [p for p in self.players.values() if p.is_empty]

    async def initialize(self):
        self._global_player_config = self.client.player_config_manager.get_global_config()
        self.client.scheduler.add_job(
            self.update_bot_activity,
            trigger="interval",
            seconds=5,
            max_instances=1,
            replace_existing=True,
            name="update_bot_activity",
            coalesce=True,
            id=f"{self.bot.user.id}-update_bot_activity",
        )

    async def destroy(self, guild_id: int, requester: discord.Member | None):
        """
        Removes a player from cache, and also Lavalink if applicable.
        Ensure you have disconnected the given guild_id from the voicechannel
        first, if connected.
        Warning
        -------
        This should only be used if you know what you're doing. Players should never be
        destroyed unless they have been moved to another :class:`Node`.
        Parameters
        ----------
        guild_id: int
            The guild_id associated with the player to remove.
        requester: :class:`discord.Member`
            The member requesting the player to be removed.
        """
        if guild_id not in self.players:
            return

        player = self.players.pop(guild_id)

        await player.disconnect(requester=requester, maybe_resuming=ENABLE_NODE_RESUMING)
        # noinspection PyProtectedMember
        player.node._logger.debug("Successfully destroyed player %s", guild_id)

    async def save_and_restore(self, guild_id: int):
        await asyncio.sleep(5)
        if player := self.players.pop(guild_id, None):
            await player.save()
            await player.disconnect(requester=self.client.bot.user)
        player_state = await self.client.player_state_db_manager.fetch_player(guild_id)
        if player_state:
            await self._restore_player(player_state)

    def find_all(self, predicate=None):
        """Returns a list of players that match the given predicate.

        Parameters
        ----------
        predicate: Optional[:class:`function`]
            A predicate to return specific players. Defaults to `None`.
        Returns
        -------
        List[:class:`Player`]
        """
        return [p for p in self.players.values() if bool(predicate(p))] if predicate else list(self.players.values())

    async def remove(self, guild_id: int) -> None:
        """Removes a player from the internal cache.

        Parameters
        ----------
        guild_id: :class:`int`
            The player that will be removed.
        """
        if guild_id in self.players:
            player = self.players.pop(guild_id)
            player.cleanup()

    def get(self, guild_id: int) -> Player:
        """
        Gets a player from cache.
        Parameters
        ----------
        guild_id: :class:`int`
            The guild_id associated with the player to get.
        Returns
        -------
        Optional[:class:`Player`]
        """
        return self.players.get(guild_id)

    async def create(
        self,
        channel: discord.channel.VocalGuildChannel,
        endpoint: str = None,
        node: Node = None,
        self_deaf: bool = None,
        requester: discord.Member = None,
        feature: str | None = None,
    ) -> Player:
        """
        Creates a player if one doesn't exist with the given information.
        If node is provided, a player will be created on that node.
        If endpoint is provided, PyLav will attempt to parse the region from the endpoint
        and return a node in the parsed region.
        If node, region and endpoint are left unspecified, or region/endpoint selection fails,
        PyLav will fall back to the node with the lowest penalty.
        Region can be omitted if node is specified and vice-versa.
        Parameters
        ----------
        channel: :class:`discord.channel.VocalGuildChannel`
            The voice channel to connect to.
        endpoint: :class:`str`
            The address of the Discord voice server. Defaults to `None`.
        node: :class:`Node`
            The node to put the player on. Defaults to `None` and a node with the lowest penalty is chosen.
        requester: :class:`discord.Member`
            The member requesting the player. Defaults to `None`.
        feature: Optional[:class:`str`]
            The feature to look for for the initial Node. Defaults to `None`.
        self_deaf: :class:`bool`
            Whether the player should deafen themselves. Defaults to `False`.
        Returns
        -------
        :class:`Player`
        """
        if p := self.players.get(channel.guild.id):
            if channel.id != p.channel_id:
                await p.move_to(requester, channel)
            return p

        region = self.client.node_manager.get_region(endpoint)

        best_node = node or await self.client.node_manager.find_best_node(region, feature=feature or None)
        if not best_node:
            raise NoNodeAvailableException("No available nodes!")
        player_config = self.client.player_config_manager.get_config(channel.guild.id)
        forced_channel_id = await player_config.fetch_forced_channel_id()
        self_deafen = await self.client.player_config_manager.get_self_deaf(channel.guild.id)
        if forced_channel_id != 0:
            act_channel = channel.guild.get_channel_or_thread(forced_channel_id)
        else:
            act_channel = channel
        player: Player = await act_channel.connect(
            cls=Player, self_deaf=self_deafen if self_deaf is None else self_deaf  # type: ignore
        )
        self.players[channel.guild.id] = player
        try:
            best_node = node or await self.client.node_manager.find_best_node(
                region, feature=feature or None, coordinates=player.coordinates
            )
            if not best_node:
                raise NoNodeAvailableException(_("There are no nodes available currently."))
            await player.post_init(
                node=best_node, player_manager=self, config=player_config, pylav=self.client, requester=requester
            )
            await player.move_to(
                requester, channel=player.channel, self_deaf=self_deafen if self_deaf is None else self_deaf
            )
            best_node.dispatch_event(PlayerConnectedEvent(player, requester or self.client.bot.user))
            # noinspection PyProtectedMember
            best_node._logger.debug("Successfully created player for %s", channel.guild.id)
            return player
        except Exception:
            LOGGER.error("Failed to create player for %s", channel.guild.id)
            LOGGER.debug("Error in create player for %s", channel.guild.id, exc_info=True)
            await player.disconnect(requester=requester)
            raise

    async def save_all_players(self) -> None:
        LOGGER.debug("Saving player states")
        await self.client.player_state_db_manager.save_players(
            [await p.to_dict() for p in self.connected_players if p.is_active]
        )

    async def restore_player_states(self) -> None:
        # noinspection PyProtectedMember
        await asyncio.wait_for(self.client._wait_for_playlists.wait(), timeout=600)
        LOGGER.info("Restoring player states")
        while not self.client.node_manager.available_nodes:
            await asyncio.sleep(1)
        tasks = [
            asyncio.create_task(self._restore_player(p))
            async for p in self.client.player_state_db_manager.fetch_all_players()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        LOGGER.info("Restored %s player states", len(self.players))

    async def _restore_player(self, player_state: PlayerState) -> None:
        player = self.players.get(player_state.id)
        if player is not None:
            # Player was started before restore
            LOGGER.debug("Player %s initialized before restore, skipping restore", player_state.id)
            await self.client.player_state_db_manager.delete_player(guild_id=player_state.id)
            return
        channel = self.client.bot.get_channel(player_state.channel_id)
        if not channel:
            # Channel does not exist anymore
            LOGGER.debug("Channel for %s could not be found, skipping player restore", player_state.id)
            await self.client.player_state_db_manager.delete_player(guild_id=player_state.id)
            return
        if not player_state.current:
            # Player was empty
            LOGGER.debug("Player %s does not have a current track, skipping restore", player_state.id)
            await self.client.player_state_db_manager.delete_player(guild_id=player_state.id)
            return
        requester = self.client.bot.user
        try:
            async with asyncio.timeout(10):
                discord_player = await self.create(
                    channel=channel,
                    requester=requester,
                    feature=(await Query.from_base64(player_state.current["encoded"], lazy=True)).requires_capability,
                    self_deaf=player_state.self_deaf,
                )
        except Exception:
            LOGGER.exception("Failed to restore player %s - %s", player_state.id, player_state.channel_id)
            raise
        # noinspection PyProtectedMember
        if not discord_player._restored:
            await discord_player.restore(player_state, requester)

    async def shutdown(self) -> None:
        LOGGER.info("Shutting down all players")
        tasks = [
            asyncio.create_task(self.destroy(guild_id=guild_id, requester=self.client.bot.user))
            for guild_id in self.players
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def update_bot_activity(self) -> None:
        """
        Updates the bot's activity.
        """
        with contextlib.suppress(asyncio.exceptions.CancelledError, asyncpg.exceptions.CannotConnectNowError):
            if not await self.client.lib_db_manager.get_config().fetch_update_bot_activity():
                return
            playing_players = len(self.playing_players)
            activities = self.bot.guilds[0].me.activities
            activity = discord.utils.find(lambda a: a.type == discord.ActivityType.listening, activities)
            if playing_players > 1:
                if (not activity) or _("Music in {number_of_servers_variable_do_not_translate} servers").format(
                    number_of_servers_variable_do_not_translate=playing_players
                ) not in activity.name:
                    LOGGER.verbose("Updating bot activity to %s", f"Listening to Music in {playing_players} servers")
                    await self.bot.change_presence(
                        activity=discord.Activity(
                            type=discord.ActivityType.listening,
                            name=shorten_string(
                                max_length=100,
                                string=_("Music in {number_of_servers_variable_do_not_translate} servers").format(
                                    number_of_servers_variable_do_not_translate=playing_players
                                ),
                            ),
                        )
                    )
            elif playing_players == 1:
                current_player = self.playing_players[0]
                if current_player.current is None:
                    return
                track_name = await current_player.current.get_track_display_name(
                    max_length=40,
                    author=True,
                    unformatted=True,
                    escape=False,
                )
                if activity and track_name in activity.name:
                    return
                LOGGER.verbose("Updating bot activity to %s", f"Listening to {track_name}")
                await self.bot.change_presence(
                    activity=discord.Activity(type=discord.ActivityType.listening, name=track_name)
                )

            elif playing_players == 0 and activity:
                LOGGER.verbose("Removing bot activity")
                await self.bot.change_presence(activity=None)
