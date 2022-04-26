from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Iterator

import discord
from red_commons.logging import getLogger

from pylav.events import PlayerConnectedEvent
from pylav.player import Player
from pylav.sql.models import PlayerModel

if TYPE_CHECKING:
    from pylav.client import Client

from pylav.exceptions import NoNodeAvailable
from pylav.node import Node

LOGGER = getLogger("red.PyLink.PlayerManager")


class PlayerManager:
    """
    Represents the player manager that contains all the players.
    len(x):
        Returns the total amount of cached players.
    iter(x):
        Returns an iterator of all the players cached.
    Attributes
    ----------
    players: :class:`dict`
        Cache of all the players that Lavalink has created.
    default_player_class: :class:`BasePlayer`
        The player that the player manager is initialized with.
    """

    def __init__(self, lavalink: Client, player: type[Player] = Player):  # type: ignore
        if not issubclass(player, Player):
            raise ValueError("Player must implement Player.")

        self.client = lavalink
        self.players: dict[int, Player] = {}
        self.default_player_class = player

    def __len__(self):
        return len(self.players)

    def __iter__(self) -> Iterator[tuple[int, Player]]:
        """Returns an iterator that yields a tuple of (guild_id, player)."""
        yield from self.players.items()

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

        if player.node and player.node.available:
            await player.node.send(op="destroy", guildId=player.guild_id)
        await player.disconnect(requester=requester)
        LOGGER.debug("[NODE-%s] Successfully destroyed player %s", player.node.name, guild_id)

    def players(self) -> Iterator[Player]:
        """Returns an iterator that yields only values."""
        yield from self.players.values()

    def find_all(self, predicate=None):
        """
        Returns a list of players that match the given predicate.
        Parameters
        ----------
        predicate: Optional[:class:`function`]
            A predicate to return specific players. Defaults to `None`.
        Returns
        -------
        List[:class:`Player`]
        """
        if not predicate:
            return list(self.players.values())

        return [p for p in self.players.values() if bool(predicate(p))]

    @property
    def connected_players(self) -> list[Player]:
        """Returns a list of all the connected players."""
        return [p for p in self.players.values() if p.is_connected]

    @property
    def playing_players(self) -> list[Player]:
        """Returns a list of all the playing players."""
        return [p for p in self.players.values() if p.is_playing]

    @property
    def not_playing_players(self) -> list[Player]:
        """Returns a list of all the not playing players."""
        return [p for p in self.players.values() if not p.is_playing]

    @property
    def paused_players(self) -> list[Player]:
        """Returns a list of all the paused players."""
        return [p for p in self.players.values() if p.paused]

    @property
    def empty_players(self) -> list[Player]:
        """Returns a list of all the empty players."""
        return [p for p in self.players.values() if p.is_empty]

    async def remove(self, guild_id: int) -> None:
        """
        Removes a player from the internal cache.
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
        channel: discord.VoiceChannel,
        endpoint: str = None,
        node: Node = None,
        self_deaf: bool = False,
        requester: discord.Member = None,
    ) -> Player:
        """
        Creates a player if one doesn't exist with the given information.
        If node is provided, a player will be created on that node.
        If endpoint is provided, Lavalink.py will attempt to parse the region from the endpoint
        and return a node in the parsed region.
        If node, region and endpoint are left unspecified, or region/endpoint selection fails,
        Lavalink.py will fall back to the node with the lowest penalty.
        Region can be omitted if node is specified and vice-versa.
        Parameters
        ----------
        channel: :class:`discord.VoiceChannel`
            The voice channel to connect to.
        endpoint: :class:`str`
            The address of the Discord voice server. Defaults to `None`.
        node: :class:`Node`
            The node to put the player on. Defaults to `None` and a node with the lowest penalty is chosen.
        self_deaf: :class:`bool`
            Whether the player should deafen themselves. Defaults to `False`.
        requester: :class:`discord.Member`
            The member requesting the player. Defaults to `None`.
        Returns
        -------
        :class:`Player`
        """
        if p := self.players.get(channel.guild.id):
            if channel.id != p.channel_id:
                await p.move_to(requester, channel, self_deaf=self_deaf)
            return p

        region = self.client.node_manager.get_region(endpoint)

        best_node = node or self.client.node_manager.find_best_node(region)
        if not best_node:
            raise NoNodeAvailable("No available nodes!")
        player: Player = await channel.connect(cls=Player)  # type: ignore
        await player.post_init(node=best_node, player_manager=self)
        await player.move_to(requester, channel=player.channel, self_deaf=self_deaf)
        await best_node.dispatch_event(PlayerConnectedEvent(player, requester))
        self.players[channel.guild.id] = player
        LOGGER.info("[NODE-%s] Successfully created player for %s", best_node.name, channel.guild.id)
        return player

    async def save_all_players(self) -> None:
        LOGGER.debug("Saving player states...")
        await self.client.player_config_manager.save_players([p.to_dict() for p in self.players.values()])

    async def restore_player_states(self) -> None:
        LOGGER.info("Restoring player states...")
        while not self.client.node_manager.available_nodes:
            await asyncio.sleep(1)
        tasks = [
            asyncio.create_task(self._restore_player(p))
            async for p in self.client.player_config_manager.get_all_players()
        ]
        await asyncio.gather(*tasks)

    async def _restore_player(self, player_state: PlayerModel) -> None:
        player = self.players.get(player_state.id)
        if player is not None:
            # Player was started before restore
            return
        channel = self.client.bot.get_channel(player_state.channel_id)
        requester = self.client.bot.user
        self_deaf = player_state.self_deaf
        discord_player = await self.create(channel=channel, requester=requester, self_deaf=self_deaf)
        await discord_player.restore(player_state, requester)

    async def shutdown(self) -> None:
        LOGGER.info("Shutting down all players...")
        tasks = [
            asyncio.create_task(self.destroy(guild_id=guild_id, requester=self.client.bot.user))
            for guild_id in self.players
        ]
        await asyncio.gather(*tasks)
