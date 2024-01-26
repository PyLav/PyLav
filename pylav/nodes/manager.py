from __future__ import annotations

import asyncio
import operator
import os
from functools import partial
from typing import TYPE_CHECKING

import aiohttp
import asyncstdlib

from pylav.compat import json
from pylav.constants.builtin_nodes import BUNDLED_NODES_IDS_HOST_MAPPING, PYLAV_BUNDLED_NODES_SETTINGS
from pylav.constants.config import EXTERNAL_UNMANAGED_NAME, JAVA_EXECUTABLE
from pylav.constants.coordinates import DEFAULT_REGIONS, REGION_TO_COUNTRY_COORDINATE_MAPPING
from pylav.events.node import NodeConnectedEvent, NodeDisconnectedEvent
from pylav.exceptions.client import PyLavNotInitializedException
from pylav.helpers.misc import ExponentialBackoffWithReset
from pylav.logging import getLogger
from pylav.nodes.node import Node
from pylav.nodes.utils import sort_key_nodes
from pylav.players.player import Player
from pylav.storage.models.node.mocked import NodeMock
from pylav.utils.location import get_closest_region_name_and_coordinate

if TYPE_CHECKING:
    from pylav.core.client import Client

LOGGER = getLogger("PyLav.NodeManager")


class NodeManager:
    """Manages nodes and their connections to the client."""

    __slots__ = (
        "_client",
        "_session",
        "_player_queue",
        "_unmanaged_external_host",
        "_unmanaged_external_password",
        "_unmanaged_external_port",
        "_unmanaged_external_ssl",
        "_nodes",
        "_adding_nodes",
        "_player_migrate_task",
    )

    def __init__(
        self,
        client: Client,
        external_host: str = None,
        external_password: str = None,
        external_port: int = None,
        external_ssl: bool = False,
    ):
        self._client = client
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120), json_serialize=json.dumps)
        self._player_queue = set()
        self._unmanaged_external_host = external_host
        self._unmanaged_external_password = external_password
        self._unmanaged_external_port = external_port
        self._unmanaged_external_ssl = external_ssl
        self._nodes = []
        self._adding_nodes = asyncio.Event()
        self._player_migrate_task = None

    def __iter__(self):
        yield from self._nodes

    @property
    def session(self) -> aiohttp.ClientSession:
        """Returns the aiohttp session used by the client"""
        return self._session

    @property
    def client(self) -> Client:
        """Returns the client"""
        return self._client

    @property
    def nodes(self) -> list[Node]:
        """Returns a list of all nodes"""
        return self._nodes

    @property
    def available_nodes(self) -> list[Node]:
        """Returns a list of available nodes"""
        return list(filter(operator.attrgetter("available"), self.nodes))

    @property
    def managed_nodes(self) -> list[Node]:
        """Returns a list of nodes that are managed by the client"""
        return list(filter(operator.attrgetter("managed"), self.nodes))

    @property
    def search_only_nodes(self) -> list[Node]:
        """Returns a list of nodes that are search only"""
        return list(filter(operator.attrgetter("available", "search_only"), self.nodes))

    @property
    def player_queue(self) -> list[Player]:
        """Returns a list of players that are queued to be played"""
        return list(self._player_queue)

    @player_queue.setter
    def player_queue(self, players: list[Player]) -> None:
        """Sets the player queue"""
        self._player_queue = set(players)

    @player_queue.deleter
    def player_queue(self):
        """Clears the player queue"""
        self._player_queue.clear()

    async def add_node(
        self,
        *,
        host: str,
        port: int,
        password: str,
        unique_identifier: int,
        name: str,
        resume_timeout: int = 60,
        reconnect_attempts: int = -1,
        ssl: bool = False,
        search_only: bool = False,
        disabled_sources: list[str] = None,
        managed: bool = False,
        yaml: dict | None = None,
        extras: dict = None,
        temporary: bool = False,
    ) -> Node:
        """
        Adds a node to PyLav's node manager.

        Parameters
        ----------
        host: :class:`str`
            The address of the Lavalink node.
        port: :class:`int`
            The port to use for websocket and REST connections.
        password: :class:`str`
            The password used for authentication.
        resume_timeout: Optional[:class:`int`]
            How long the node should wait for a connection while disconnected before clearing all players.
            Defaults to `60`.
        name: :class:`str`
            An identifier for the node that will show in logs. Defaults to `None`.
        reconnect_attempts: Optional[:class:`int`]
            The amount of times connection with the node will be reattempted before giving up.
            Set to `-1` for infinite. Defaults to `3`.
        ssl: Optional[:class:`bool`]
            Whether to use a ssl connection. Defaults to `False`.
        search_only: :class:`bool`
            Whether the node is search only. Defaults to `False`.
        unique_identifier: Optional[:class:`str`]
            A unique identifier for the node. Defaults to `None`.
        disabled_sources: Optional[:class:`list`[:class:`str`]]
            A list of sources to disable. Defaults to `None`.
        managed: Optional[:class:`bool`]
            Whether the node is managed by the client. Defaults to `False`.
        yaml: Optional[:class:`dict`]
            A dictionary of node settings. Defaults to `None`.
        extras: Optional[:class:`dict`]
            A dictionary of extra settings. Defaults to `{}`.
        temporary: :class:`bool`
            Whether the node is temporary. Defaults to `False`.
            Temporary nodes are not added to the db.

        Returns
        -------
        :class:`Node`
            The node that was added.
        """
        node = Node(
            manager=self,
            host=host,
            port=port,
            password=password,
            resume_timeout=resume_timeout,
            name=name,
            reconnect_attempts=reconnect_attempts,
            ssl=ssl,
            search_only=search_only,
            unique_identifier=unique_identifier,
            disabled_sources=disabled_sources,
            managed=managed,
            extras=extras or {},
            temporary=temporary,
        )
        self._nodes.append(node)

        # noinspection PyProtectedMember
        node._logger.info("Successfully added to Node Manager")
        # noinspection PyProtectedMember
        node._logger.verbose("Successfully added to Node Manager -- %r", node)

        if temporary:
            yaml = yaml or {"server": {}, "lavalink": {"server": {}}}
            yaml["server"]["address"] = host  # type: ignore
            yaml["server"]["port"] = port  # type: ignore
            yaml["lavalink"]["server"]["password"] = password
            data = {
                "name": name,
                "ssl": ssl,
                "resume_timeout": resume_timeout,
                "reconnect_attempts": reconnect_attempts,
                "search_only": search_only,
                "managed": managed,
                "extras": extras or {},
                "yaml": yaml,
                "disabled_sources": disabled_sources,
            }
            node._config = NodeMock(id=unique_identifier, data=data)

        else:
            node._config = await self.client.node_db_manager.update_node(
                host=host,
                port=port,
                password=password,
                resume_timeout=resume_timeout,
                name=name,
                reconnect_attempts=reconnect_attempts,
                ssl=ssl,
                search_only=search_only,
                unique_identifier=unique_identifier,
                disabled_sources=disabled_sources,
                managed=managed,
                yaml=yaml,
                extras=extras or {},
            )
        return node

    async def remove_node(self, node: Node) -> None:
        """
        Removes a node.
        Parameters
        ----------
        node: :class:`Node`
            The node to remove from the list.
        """
        await node.close()
        self.nodes.remove(node)
        # noinspection PyProtectedMember
        node._logger.info("Successfully removed Node")
        # noinspection PyProtectedMember
        node._logger.verbose("Successfully removed Node -- %r", node)
        if (
            node.identifier
            and not node.managed
            and node.identifier not in BUNDLED_NODES_IDS_HOST_MAPPING
            and node.identifier != 31415
        ):
            await self.client.node_db_manager.delete(node.identifier)
            # noinspection PyProtectedMember
            node._logger.debug("Successfully deleted Node from database")

    def get_region(self, endpoint: str | None) -> str | None:
        """
        Returns a region from a Discord voice server address.
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

        for key in DEFAULT_REGIONS:
            nodes = [n for n in self.available_nodes if n.region == key]

            if not nodes:
                continue

            if endpoint.startswith(key):
                return key
        return None

    def get_closest_node(self, region: str) -> Node:
        """
        Returns the closest node to a given region.
        Parameters
        ----------
        region: :class:`str`
            The region to use.
        Returns
        -------
        :class:`Node`
        """
        return min(self.available_nodes, key=lambda n: n.region_distance(region))

    async def find_best_node(
        self,
        region: str = None,
        not_region: str = None,
        feature: str = None,
        already_attempted_regions: set[str] = None,
        coordinates: tuple[float, float] = None,
        wait: bool = False,
        attempt: int = 0,
        backoff: ExponentialBackoffWithReset = None,
    ) -> Node | None:
        """Finds the best (least used) node in the given region, if applicable.
        Parameters
        ----------
        region: :class:`str`
            The region to use.
        not_region: :class:`str`
            The region to exclude.
        feature: :class:`str`
            The feature required.
        already_attempted_regions: :class:`set`[:class:`str`]
            A set of regions that have already been attempted.
        coordinates: :class:`tuple`[:class:`float`, :class:`float`]
            The coordinates to use.
        wait: :class:`bool`
            Whether to wait for a node to become available.
        attempt: :class:`int`
            The current attempt number.
        backoff: :class:`ExponentialBackoffWithReset`
            The backoff to use.
        Returns
        -------
        Optional[:class:`Node`]
        """
        if backoff is None:
            backoff = ExponentialBackoffWithReset()
            delay = 1
        else:
            delay = backoff.delay()
        already_attempted_regions = already_attempted_regions or set()
        if feature:
            nodes = [n for n in self.available_nodes if n.has_capability(feature)]
        else:
            nodes = self.available_nodes
        if coordinates is None:
            if region and region in REGION_TO_COUNTRY_COORDINATE_MAPPING:
                coordinates = REGION_TO_COUNTRY_COORDINATE_MAPPING[region]
            else:
                coordinates = (0, 0)
        if region and not_region:
            nodes = await self._get_nodes_by_region_with_exclusion(
                already_attempted_regions, coordinates, nodes, not_region, region
            )
        elif region:
            nodes = await self._get_nodes_by_region_only(already_attempted_regions, coordinates, nodes, region)
        else:
            nodes = [n for n in nodes if n.region != not_region and n.region not in already_attempted_regions]

        if not nodes:
            nodes = await self._get_fall_back_nodes(already_attempted_regions, feature, nodes)
        node = await asyncstdlib.min(nodes, key=partial(sort_key_nodes, region=region), default=None) if nodes else None
        if node is None and wait:
            await asyncio.sleep(delay)
            return await self.find_best_node(
                region=region,
                not_region=not_region,
                feature=feature,
                already_attempted_regions=already_attempted_regions,
                coordinates=coordinates,
                wait=wait,
                backoff=backoff,
                attempt=attempt + 1,
            )
        return node

    async def _get_fall_back_nodes(self, already_attempted_regions, feature, nodes):
        if feature:
            nodes = [
                n
                for n in self.available_nodes
                if n.has_capability(feature) and n.region not in already_attempted_regions
            ]
        else:
            nodes = self.available_nodes
        return nodes

    async def _get_nodes_by_region_only(self, already_attempted_regions, coordinates, nodes, region):
        available_regions = {n.region for n in self.available_nodes if n.region not in already_attempted_regions}
        closest_region, __ = await get_closest_region_name_and_coordinate(*coordinates, region_pool=available_regions)
        nodes = [
            n for n in nodes if (n.region in [region, closest_region]) and n.region not in already_attempted_regions
        ]
        return nodes

    async def _get_nodes_by_region_with_exclusion(
        self, already_attempted_regions, coordinates, nodes, not_region, region
    ):
        available_regions = {n.region for n in self.available_nodes if n.region not in already_attempted_regions}
        closest_region, __ = await get_closest_region_name_and_coordinate(*coordinates, region_pool=available_regions)
        nodes = [
            n
            for n in nodes
            if (n.region in [region, closest_region])
            and n.region != not_region
            and n.region not in already_attempted_regions
        ]
        return nodes

    def get_node_by_id(self, unique_identifier: int) -> Node | None:
        """
        Returns a node by its unique identifier.
        Parameters
        ----------
        unique_identifier: :class:`int`
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
        # noinspection PyProtectedMember
        node._logger.debug("Successfully established connection")
        del node.down_votes
        self._player_migrate_task = asyncio.create_task(self._player_change_node_task(node))
        self.client.dispatch_event(NodeConnectedEvent(node))

    async def _player_change_node_task(self, node):
        for player in iter(self.player_queue):
            await player.change_node(node, forced=True)
            # noinspection PyProtectedMember
            node._logger.debug("Successfully moved %s", player.guild.id)
        # noinspection PyProtectedMember
        if self.client._connect_back:
            # noinspection PyProtectedMember
            for player in iter(node._original_players):
                await player.change_node(node, forced=True)
                player._original_node = None
        del self.player_queue
        self._player_migrate_task = None

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
        if self.client.is_shutting_down:
            return
        # noinspection PyProtectedMember
        node._logger.warning("Disconnected with code %s and reason %s", code, reason)
        # noinspection PyProtectedMember
        node._logger.verbose(
            "Disconnected with code %s and reason %s -- %r",
            code,
            reason,
            node,
        )
        self.client.dispatch_event(NodeDisconnectedEvent(node, code, reason))
        best_node = await self.find_best_node(region=node.region)
        if not best_node or not best_node.available:
            self.player_queue = self.player_queue + node.players
            LOGGER.error("Unable to move players, no available nodes! Waiting for a node to become available")
            return

        for player in iter(node.players):
            await player.change_node(best_node, forced=True)
            # noinspection PyProtectedMember
            if self.client._connect_back:
                player._original_node = node

    async def close(self) -> None:
        """Disconnects all nodes and closes the session."""
        if self._player_migrate_task is not None:
            self._player_migrate_task.cancel()
        await self.session.close()
        for node in iter(self.nodes):
            await node.close()

    async def connect_to_all_nodes(self) -> None:
        """Connects to all nodes."""
        nodes_list = []
        for node in iter(await self.client.node_db_manager.get_all_unmanaged_nodes()):
            await self._process_single_unmanaged_node_connection(node, nodes_list)
        await self._process_envvar_node(nodes_list)
        # noinspection PyProtectedMember
        config_data = self.client._lib_config_manager.get_config()
        all_data = await config_data.fetch_all()

        if all_data["java_path"] != JAVA_EXECUTABLE and os.path.exists(JAVA_EXECUTABLE):
            await config_data.update_java_path(JAVA_EXECUTABLE)

        tasks = [asyncio.create_task(n.wait_until_ready()) for n in nodes_list]
        if not tasks:
            if await self.client.managed_node_is_enabled():
                self._adding_nodes.set()
                return True
            LOGGER.warning("No nodes found, please add some nodes")
            raise PyLavNotInitializedException("Failed to connect to any nodes")
        done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
        for task in pending:
            task.cancel()
        for result in done:
            result.result()
        len_nodes = sum(1 for node in nodes_list if node.available)
        if len_nodes == 0:
            raise PyLavNotInitializedException("No nodes are available")
        if not self._adding_nodes.is_set():
            self._adding_nodes.set()
        return True

    async def _process_bundled_node_lava_link(self, nodes_list):
        if all(True for n in iter(nodes_list) if n.host != "lava.link"):
            nodes_list.append(
                await self.add_node(
                    password=f"PyLav/{self.client.lib_version}",
                    **PYLAV_BUNDLED_NODES_SETTINGS["lava.link"],
                )
            )
        else:
            LOGGER.debug(
                "%s already added to connection pool - skipping duplicated connection",
                PYLAV_BUNDLED_NODES_SETTINGS["lava.link"]["name"],
            )

    async def _process_bundled_node_ny(self, nodes_list):
        if all(True for n in iter(nodes_list) if n.host != "ll-us-ny.draper.wtf") and not self.get_node_by_id(
            PYLAV_BUNDLED_NODES_SETTINGS["ll-us-ny.draper.wtf"]["unique_identifier"]
        ):
            base_settings = PYLAV_BUNDLED_NODES_SETTINGS["ll-us-ny.draper.wtf"]
            nodes_list.append(await self.add_node(**base_settings))
        else:
            LOGGER.debug(
                "%s already added to connection pool - skipping duplicated connection",
                PYLAV_BUNDLED_NODES_SETTINGS["ll-us-ny.draper.wtf"]["name"],
            )

    async def _process_bundled_node_london(self, nodes_list):
        if all(True for n in iter(nodes_list) if n.host != "ll-gb.draper.wtf") and not self.get_node_by_id(
            PYLAV_BUNDLED_NODES_SETTINGS["ll-gb.draper.wtf"]["unique_identifier"]
        ):
            base_settings = PYLAV_BUNDLED_NODES_SETTINGS["ll-gb.draper.wtf"]
            base_settings["host"] = "ll-gb.draper.wtf"
            nodes_list.append(await self.add_node(**base_settings))
        else:
            LOGGER.debug(
                "%s already added to connection pool - skipping duplicated connection",
                PYLAV_BUNDLED_NODES_SETTINGS["ll-gb.draper.wtf"]["name"],
            )

    async def _process_envvar_node(self, nodes_list):
        if self._unmanaged_external_host and self._unmanaged_external_password:
            if all(True for n in nodes_list if n.host != self._unmanaged_external_host):
                if self._unmanaged_external_host in PYLAV_BUNDLED_NODES_SETTINGS:
                    base_settings = PYLAV_BUNDLED_NODES_SETTINGS[self._unmanaged_external_host]
                else:
                    base_settings = {
                        "port": self._unmanaged_external_port or (443 if self._unmanaged_external_ssl else 80),
                        "ssl": self._unmanaged_external_ssl,
                        "password": self._unmanaged_external_password,
                        "resume_timeout": 600,
                        "reconnect_attempts": -1,
                        "search_only": False,
                        "managed": False,
                        "disabled_sources": [],
                        "host": self._unmanaged_external_host,
                        "unique_identifier": 31415,
                        "name": EXTERNAL_UNMANAGED_NAME,
                        "temporary": True,
                    }
                nodes_list.append(await self.add_node(**base_settings))
            else:
                LOGGER.warning(
                    "%s already added to connection pool - skipping duplicated connection - (%s:%s)",
                    EXTERNAL_UNMANAGED_NAME,
                    self._unmanaged_external_host,
                    self._unmanaged_external_port,
                )

    async def _process_single_unmanaged_node_connection(self, node, nodes_list):
        if node.id == self.client.bot.user.id:
            LOGGER.debug("Skipping node %s as it is the managed node", node.id)
            return
        node_data = await node.fetch_all()
        try:
            if node in nodes_list:
                LOGGER.warning(
                    "%s Node already added to connection pool - skipping duplicated connection - (%s:%s)",
                    node_data["name"],
                    node_data["yaml"]["server"]["address"],
                    node_data["yaml"]["server"]["port"],
                )
                return
            if node_data["yaml"]["server"]["address"] in PYLAV_BUNDLED_NODES_SETTINGS:
                connection_arguments = PYLAV_BUNDLED_NODES_SETTINGS[node_data["yaml"]["server"]["address"]]
            else:
                connection_arguments = await node.get_connection_args()
            nodes_list.append(await self.add_node(**connection_arguments))
        except (ValueError, KeyError) as exc:
            LOGGER.warning("Invalid node, skipping ... id: %s - Original error: %s", node.id, exc)

    async def wait_until_ready(self, timeout: float | None = None):
        """Wait until all nodes are ready."""
        await asyncio.wait_for(self._adding_nodes.wait(), timeout=timeout)
