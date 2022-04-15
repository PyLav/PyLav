from __future__ import annotations

import asyncio
import itertools
import random
from collections import defaultdict
from pathlib import Path
from typing import Callable

import aiohttp
import discord
import ujson
from red_commons.logging import getLogger
from redbot.core.bot import Red

from pylav._config import __VERSION__, CONFIG_DIR
from pylav._lib_config import LibConfigManager  # noqa
from pylav.cache import CacheManager
from pylav.config import ConfigManager
from pylav.equalizers import EqualizerManager
from pylav.events import Event
from pylav.exceptions import NodeError
from pylav.managed_node import LocalNodeManager
from pylav.node import Node
from pylav.node_manager import NodeManager
from pylav.player import Player
from pylav.player_manager import PlayerManager
from pylav.player_state import PlayerStateManager
from pylav.playlists import PlaylistManager

LOGGER = getLogger("red.PyLink.Client")


class Client:
    """
    Represents a Lavalink client used to manage nodes and connections.

    .. _event loop: https://docs.python.org/3/library/asyncio-eventloop.html

    Parameters
    ----------
    bot : :class:`discord.Client`
        The bot instance.
    player: Optional[:class:`Player`]
        The class that should be used for the player. Defaults to ``Player``.
        Do not change this unless you know what you are doing!
    regions: Optional[:class:`dict`]
        A dictionary representing region -> discord endpoint. You should only
        change this if you know what you're doing and want more control over
        which regions handle specific locations. Defaults to `None`.
    connect_back: Optional[:class:`bool`]
        A boolean that determines if a player will connect back to the
        node it was originally connected to. This is not recommended doing since
        the player will most likely be performing better in the new node. Defaults to `False`.

        Warning
        -------
        If this option is enabled and the player's node is changed through `Player.change_node` after
        the player was moved via the fail-over mechanism, the player will still move back to the original
        node when it becomes available. This behaviour can be avoided in custom player implementations by
        setting `self._original_node` to `None` in the `change_node` function.

    Attributes
    ----------
    node_manager: :class:`NodeManager` # noqa
        Represents the node manager that contains all lavalink nodes.
    player_manager: :class:`PlayerManager`
        Represents the player manager that contains all the players.
    player_state_manager: :class:`PlayerStateManager`
        Represents the player state manager that is used to save/ready player states.
    config_manager: :class:`ConfigManager`
        Represents the config manager that is used to save/load configs.
    equalizer_manager: :class:`EqualizerManager`
        Represents the equalizer manager that is used to save/load equalizers.
    cache_manager: :class:`CacheManager`
        Represents the cache manager that is used to save/load cache data.
    playlists: :class:`PlaylistManager`
        Represents the playlist manager that is used to save/load playlists.
    """

    _event_hooks = defaultdict(list)
    _cache_manager: CacheManager
    _config_manager: ConfigManager
    _equalizer_manager: EqualizerManager
    _player_state_manager: PlayerStateManager
    _playlist_manager: PlaylistManager
    _local_node_manager: LocalNodeManager

    def __init__(
        self,
        bot: Red | discord.Client,
        player=Player,
        regions: dict = None,
        connect_back: bool = False,
        config_folder: Path = CONFIG_DIR,
    ):
        self._config_folder = Path(config_folder)
        self._bot = bot
        self._user_id = str(bot.user.id)
        self._node_manager = NodeManager(self, regions)
        self._player_manager = PlayerManager(self, player)
        self._lib_config_manager = LibConfigManager(self)

        self._connect_back = connect_back
        self._warned_about_no_search_nodes = False
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), json_serialize=ujson.dumps)

    async def init(self):
        config_data = await self._lib_config_manager.get_config()
        if not config_data:
            config_data = await self.set_lib_config(
                config_folder=self._config_folder,
                db_connection_string="sqlite+aiosqlite:///",
                java_path="java",
                enable_managed_node=True,
                auto_update_managed_nodes=True,
            )

        connection_string = config_data.get("db_connection_string")
        auto_update_managed_nodes = config_data.get("auto_update_managed_nodes", False)
        enable_managed_node = config_data.get("enable_managed_node", False)
        self._config_folder = Path(config_data.get("config_folder"))
        self._cache_manager = CacheManager(
            self, config_folder=self._config_folder, sql_connection_string=connection_string
        )
        self._config_manager = ConfigManager(
            self, config_folder=self._config_folder, sql_connection_string=connection_string
        )
        self._equalizer_manager = EqualizerManager(
            self, config_folder=self._config_folder, sql_connection_string=connection_string
        )
        self._player_state_manager = PlayerStateManager(
            self, config_folder=self._config_folder, sql_connection_string=connection_string
        )
        self._playlist_manager = PlaylistManager(
            self, config_folder=self._config_folder, sql_connection_string=connection_string
        )
        self._local_node_manager = LocalNodeManager(self, auto_update=auto_update_managed_nodes)
        if enable_managed_node:
            await self._local_node_manager.start(java_path=config_data.get("java_path"))

    async def set_lib_config(
        self,
        config_folder: Path | str,
        db_connection_string: str,
        java_path: str,
        enable_managed_node: bool,
        auto_update_managed_nodes: bool,
    ):
        config_folder = Path(config_folder)
        if config_folder.is_file():
            raise ValueError("The config folder must be a directory.")
        if config_folder.is_dir() and not config_folder.exists():
            config_folder.mkdir(parents=True)

        if db_connection_string.startswith("sqlite"):
            db_connection_string = "sqlite+aiosqlite:///"
        elif db_connection_string.startswith("mysql"):
            if db_connection_string.startswith("mysql") and not db_connection_string.startswith("mysql+asyncmy://"):
                raise ValueError(
                    "MySQL connection string must be formatted like `mysql+asyncmy://user:password@host:port/dbname`."
                )
            else:
                LOGGER.debug("MySQL connection string set to %s.", db_connection_string)
        elif db_connection_string.startswith("postgresql"):
            if not db_connection_string.startswith("postgresql+asyncpg://"):
                raise ValueError(
                    "Postgresql connection string must be formatted like "
                    "`postgresql+asyncpg://user:password@host:port/dbname`."
                )
            else:
                LOGGER.debug("Postgresql connection string set to %s.", db_connection_string)
        else:
            raise ValueError("Invalid connection string, SQL, MySQL, or Postgresql connection string required.")

        self._config_folder = config_folder
        return await self._lib_config_manager.upsert_config(
            {
                "id": 1,
                "db_connection_string": db_connection_string,
                "config_folder": str(config_folder),
                "java_path": java_path,
                "enable_managed_node": enable_managed_node,
                "auto_update_managed_nodes": auto_update_managed_nodes,
            }
        )

    @property
    def managed_node_controller(self) -> LocalNodeManager:
        return self._local_node_manager

    @property
    def node_manager(self) -> NodeManager:
        return self._node_manager

    @property
    def player_manager(self) -> PlayerManager:
        return self._player_manager

    @property
    def cache_manager(self) -> CacheManager:
        return self._cache_manager

    @property
    def config_manager(self) -> ConfigManager:
        return self._config_manager

    @property
    def equalizer_manager(self) -> EqualizerManager:
        return self._equalizer_manager

    @property
    def player_state_manager(self) -> PlayerStateManager:
        return self._player_state_manager

    @property
    def playlist_manager(self) -> PlaylistManager:
        return self._playlist_manager

    @property
    def config_folder(self) -> Path:
        return self._config_folder

    @property
    def bot(self) -> Red | discord.Client:
        return self._bot

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def lib_version(self) -> str:
        return __VERSION__

    @property
    def bot_id(self) -> str:
        return self._user_id

    def add_event_hook(self, hook: Callable):
        if hook not in self._event_hooks["Generic"]:
            self._event_hooks["Generic"].append(hook)

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
    ):
        """
        Adds a node to Lavalink's node manager.

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
            An identifier for the node that will show in logs. Defaults to `None`
        reconnect_attempts: Optional[:class:`int`]
            The amount of times connection with the node will be reattempted before giving up.
            Set to `-1` for infinite. Defaults to `3`.
        ssl: Optional[:class:`bool`]
            Whether to use SSL for the connection. Defaults to `False`.
        """

        self.node_manager.add_node(
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

    async def get_tracks(
        self, query: str, node: Node = None, search_only_nodes: bool = False, first: bool = False
    ) -> dict | list[dict]:
        """|coro|
        Gets all tracks associated with the given query.

        Parameters
        ----------
        query: :class:`str`
            The query to perform a search for.
        node: Optional[:class:`Node`]
            The node to use for track lookup. Leave this blank to use a random node.
            Defaults to `None` which is a random node.
                search_only_nodes: Optional[:class:`bool`]
            Whether to only search for tracks using nodes flagged as search only.
        search_only_nodes: Optional[:class:`bool`]
            Whether to only search for tracks using nodes flagged as search only.
        first: Optional[:class:`bool`]
            Whether to only return the first track. Defaults to `False`.

        Returns
        -------
        :class:`list` of :class:`dict`
            A dict representing tracks.
        """
        if search_only_nodes:
            nodes = self.node_manager.search_only_nodes
            if not nodes:
                if not self._warned_about_no_search_nodes:
                    LOGGER.warning("No search only nodes available, defaulting to all available nodes.")
                    self._warned_about_no_search_nodes = True
                nodes = self.node_manager.available_nodes
        else:
            nodes = self.node_manager.available_nodes

        if not nodes:
            raise NodeError("No available nodes!")
        node = node or random.choice(list(nodes))
        return await node.get_tracks(query, first=first)

    async def decode_track(self, track: str, node: Node = None) -> dict | None:
        """|coro|
        Decodes a base64-encoded track string into a dict.

        Parameters
        ----------
        track: :class:`str`
            The base64-encoded `track` string.
        node: Optional[:class:`Node`]
            The node to use for the query. Defaults to `None` which is a random node.

        Returns
        -------
        :class:`dict`
            A dict representing the track's information.
        """
        if not self.node_manager.available_nodes:
            raise NodeError("No available nodes!")
        node = node or random.choice(list(self.node_manager.available_nodes))
        return await node.decode_track(track)

    async def decode_tracks(self, tracks: list, node: Node = None) -> list[dict]:
        """|coro|
        Decodes a list of base64-encoded track strings into a dict.

        Parameters
        ----------
        tracks: list[:class:`str`]
            A list of base64-encoded `track` strings.
        node: Optional[:class:`Node`]
            The node to use for the query. Defaults to `None` which is a random node.

        Returns
        -------
        List[:class:`dict`]
            A list of dicts representing track information.
        """
        if not self.node_manager.available_nodes:
            raise NodeError("No available nodes!")
        node = node or random.choice(list(self.node_manager.available_nodes))
        return await node.decode_tracks(tracks)

    @staticmethod
    async def routeplanner_status(node: Node) -> dict | None:
        """|coro|
        Gets the route-planner status of the target node.

        Parameters
        ----------
        node: :class:`Node`
            The node to use for the query.

        Returns
        -------
        :class:`dict`
            A dict representing the route-planner information.
        """
        return await node.routeplanner_status()

    @staticmethod
    async def routeplanner_free_address(node: Node, address: str) -> bool:
        """|coro|
        Gets the route-planner status of the target node.

        Parameters
        ----------
        node: :class:`Node`
            The node to use for the query.
        address: :class:`str`
            The address to free.

        Returns
        -------
        :class:`bool`
            True if the address was freed, False otherwise.
        """
        return await node.routeplanner_free_address(address)

    @staticmethod
    async def routeplanner_free_all_failing(node: Node) -> bool:
        """|coro|
        Gets the route-planner status of the target node.

        Parameters
        ----------
        node: :class:`Node`
            The node to use for the query.

        Returns
        -------
        :class:`bool`
            True if all failing addresses were freed, False otherwise.
        """
        return await node.routeplanner_free_all_failing()

    @staticmethod
    async def _dispatch_event(event: Event):
        """|coro|
        Dispatches the given event to all registered hooks.

        Parameters
        ----------
        event: :class:`Event`
            The event to dispatch to the hooks.
        """
        generic_hooks = Client._event_hooks["Generic"]
        targeted_hooks = Client._event_hooks[type(event).__name__]

        if not generic_hooks and not targeted_hooks:
            return

        async def _hook_wrapper(hook, event_):
            try:
                await hook(event_)
            except Exception as exc:
                LOGGER.warning("Event hook %s encountered an exception!", hook.__name__)
                LOGGER.debug("Event hook %s encountered an exception!", hook.__name__, exc_info=exc)

        tasks = [_hook_wrapper(hook, event) for hook in itertools.chain(generic_hooks, targeted_hooks)]
        await asyncio.wait(tasks)

        LOGGER.debug("Dispatched %s to all registered hooks", type(event).__name__)
