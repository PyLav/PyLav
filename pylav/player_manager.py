from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

import discord
from red_commons.logging import getLogger

from pylav.exceptions import NodeError
from pylav.player import Player

if TYPE_CHECKING:
    from pylav.client import Client

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

    def __init__(self, lavalink: Client, player: Player):
        if not issubclass(player, Player):  # noqa
            raise ValueError("Player must implement Player.")

        self.client = lavalink
        self.players = {}
        self.default_player_class = player

    def __len__(self):
        return len(self.players)

    def __iter__(self):
        """Returns an iterator that yields a tuple of (guild_id, player)."""
        yield from self.players.items()

    async def destroy(self, guild_id: int):
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
        """
        if guild_id not in self.players:
            return

        player = self.players.pop(guild_id)

        if player.node and player.node.available:
            await player.node.send(op="destroy", guildId=player.guild_id)
            player.cleanup()

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

    def remove(self, guild_id: int) -> None:
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
        Returns
        -------
        :class:`Player`
        """
        if p := self.players.get(channel.guild.id):
            if channel.id != p.channel_id:
                await p.move_to(channel, self_deaf=self_deaf)
            return p

        if endpoint:  # Prioritise endpoint over region parameter
            region = self.client.node_manager.get_region(endpoint)

        best_node = node or self.client.node_manager.find_best_node(region)

        if not best_node:
            raise NodeError("No available nodes!")
        player: Player = await channel.connect(cls=Player)  # type: ignore
        player.post_init(node=best_node, player_manager=self)
        await player.move_to(channel=player.channel, self_deaf=self_deaf)

        self.players[channel.guild.id] = player
        LOGGER.debug("[NODE-%s] Successfully created player for %s", best_node.name, channel.guild.id)
        return player

    async def save_all_players(self) -> None:
        await self.client.player_state_manager.upsert_players([p.to_dict() for p in self])

    async def restore_player_states(self) -> None:
        pass
