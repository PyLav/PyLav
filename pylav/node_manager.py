from __future__ import annotations

import operator
from collections.abc import Iterator
from typing import TYPE_CHECKING

import aiohttp
from red_commons.logging import getLogger

from pylav.constants import DEFAULT_REGIONS
from pylav.events import NodeConnectedEvent, NodeDisconnectedEvent
from pylav.node import Node
from pylav.player import Player

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("red.PyLink.NodeManager")


class NodeManager:
    def __init__(self, client: Client, supported_regions: dict[str, tuple[str]] = None):
        self._client = client
        self._session = client.session
        self._player_queue = []

        self._nodes = []

        self.regions = supported_regions or DEFAULT_REGIONS

    def __iter__(self):
        yield from self._nodes

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def client(self) -> Client:
        """Returns the client."""
        return self._client

    @property
    def nodes(self) -> list[Node]:
        """Returns a list of all nodes."""
        return self._nodes

    @property
    def available_nodes(self) -> Iterator[Node]:
        """Returns a list of available nodes."""
        return filter(operator.attrgetter("available"), self.nodes)

    @property
    def search_only_nodes(self) -> Iterator[Node]:
        """Returns a list of nodes that are search only."""
        return filter(operator.attrgetter("available", "search_only"), self.nodes)

    @property
    def player_queue(self) -> list[Player]:
        """Returns a list of players that are queued to be played."""
        return self._player_queue

    @player_queue.setter
    def player_queue(self, players: list[Player]) -> None:
        """Sets the player queue."""
        self._player_queue = players

    @player_queue.deleter
    def player_queue(self):
        """Clears the player queue."""
        self._player_queue.clear()

    def add_node(
        self,
        host: str,
        port: int,
        password: str,
        region: str,
        resume_key: str = None,
        resume_timeout: int = 60,
        name: str = None,
        reconnect_attempts: int = 3,
        ssl: bool = False,
    ) -> Node:
        """
        Adds a node to PyLink's node manager.
        Parameters
        ----------
        host: :class:`str`
            The address of the Lavalink node.
        port: :class:`int`
            The port to use for websocket and REST connections.
        password: :class:`str`
            The password used for authentication.
        region: :class:`str`
            The region to assign this node to.
        resume_key: Optional[:class:`str`]
            A resume key used for resuming a session upon re-establishing a WebSocket connection to Lavalink.
            Defaults to `None`.
        resume_timeout: Optional[:class:`int`]
            How long the node should wait for a connection while disconnected before clearing all players.
            Defaults to `60`.
        name: Optional[:class:`str`]
            An identifier for the node that will show in logs. Defaults to `None`.
        reconnect_attempts: Optional[:class:`int`]
            The amount of times connection with the node will be reattempted before giving up.
            Set to `-1` for infinite. Defaults to `3`.
        ssl: Optional[:class:`bool`]
            Whether to use a ssl connection. Defaults to `False`.
        """
        node = Node(
            manager=self,
            host=host,
            port=port,
            password=password,
            region=region,
            resume_key=resume_key,
            resume_timeout=resume_timeout,
            name=name,
            reconnect_attempts=reconnect_attempts,
            ssl=ssl,
        )
        self._nodes.append(node)

        LOGGER.info("[NODE-%s] Successfully added to Node Manager", node.name)
        LOGGER.verbose("[NODE-%s] Successfully added to Node Manager -- %r", node.name, node)
        return node

    def remove_node(self, node: Node) -> None:
        """
        Removes a node.
        Parameters
        ----------
        node: :class:`Node`
            The node to remove from the list.
        """
        self.nodes.remove(node)
        LOGGER.info("[NODE-%s] Successfully removed Node", node.name)
        LOGGER.info("[NODE-%s] Successfully removed Node -- %r", node.name, node)

    def get_region(self, endpoint: str) -> str | None:
        """
        Returns a Lavalink.py-friendly region from a Discord voice server address.
        Parameters
        ----------
        endpoint: :class:`str`
            The address of the Discord voice server.
        Returns
        -------
        Optional[:class:`str`]
        """
        if not endpoint:
            return None

        endpoint = endpoint.replace("vip-", "")

        for key in self.regions:
            nodes = [n for n in self.available_nodes if n.region == key]

            if not nodes:
                continue

            if endpoint.startswith(self.regions[key]):
                return key
        return None

    def find_best_node(
        self,
        region: str = None,
        not_region: str = None,
    ) -> Node | None:
        """
        Finds the best (least used) node in the given region, if applicable.
        Parameters
        ----------
        region: Optional[:class:`str`]
            The region to find a node in. Defaults to `None`.
        not_region: Optional[:class:`str`]
            The region to exclude from the search. Defaults to `None`.
        Returns
        -------
        Optional[:class:`Node`]
        """
        if region and not_region:
            nodes = [n for n in self.available_nodes if n.region == region and n.region != not_region]
        elif region:
            nodes = [n for n in self.available_nodes if n.region == region]
        else:
            nodes = [n for n in self.available_nodes if n.region != not_region]

        if not nodes:  # If there are no regional nodes available, or a region wasn't specified.
            nodes = self.available_nodes

        if not nodes:
            return None
        best_node = min(nodes, key=operator.attrgetter("connected_count", "penalty"))
        return best_node

    def get_node_by_id(self, unique_identifier: str) -> Node | None:
        """
        Returns a node by its unique identifier.
        Parameters
        ----------
        unique_identifier: :class:`str`
            The unique identifier of the node.
        Returns
        -------
        Optional[:class:`Node`]
        """
        return next((n for n in self.nodes if n.identifier == unique_identifier), None)

    async def node_connect(self, node: Node) -> None:
        """
        Called when a node is connected from Lavalink.
        Parameters
        ----------
        node: :class:`Node`
            The node that has just connected.
        """
        LOGGER.info("[NODE-%s] Successfully established connection", node.name)

        for player in self.player_queue:
            await player.change_node(node)
            LOGGER.debug("[NODE-%s] Successfully moved %s", node.name, player.guild_id)

        if self.client._connect_back:  # noqa
            for player in node._original_players:  # noqa
                await player.change_node(node)
                player._original_node = None

        del self.player_queue
        await self.client._dispatch_event(NodeConnectedEvent(node))  # noqa

    async def node_disconnect(self, node: Node, code: int, reason: str) -> None:
        """
        Called when a node is disconnected from Lavalink.
        Parameters
        ----------
        node: :class:`Node`
            The node that has just connected.
        code: :class:`int`
            The code for why the node was disconnected.
        reason: :class:`str`
            The reason why the node was disconnected.
        """
        LOGGER.warning("[NODE-%s] Disconnected with code %s and reason %s", node.name, code, reason)
        LOGGER.verbose(
            "[NODE-%s] Disconnected with code %s and reason %s -- %r",
            node.name,
            code,
            reason,
            node,
        )
        await self.client._dispatch_event(NodeDisconnectedEvent(node, code, reason))  # noqa

        best_node = self.find_best_node(node.region)

        if not best_node:
            self.player_queue.extend(node.players)
            LOGGER.error("Unable to move players, no available nodes! Waiting for a node to become available.")
            return

        for player in node.players:
            await player.change_node(best_node)

            if self.client._connect_back:  # noqa
                player._original_node = node
