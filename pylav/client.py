from __future__ import annotations

import asyncio
import datetime
import itertools
import pathlib
import random
from collections import defaultdict
from typing import Callable

import aiohttp
import aiopath
import discord
import ujson
from asyncspotify import Client as SpotifyClient
from asyncspotify import ClientCredentialsFlow
from discord.abc import Messageable
from discord.ext.commands import Cog
from discord.types.embed import EmbedType
from red_commons.logging import getLogger

from pylav._config import __VERSION__, CONFIG_DIR
from pylav._lib_config import LibConfigManager  # noqa
from pylav.config import ConfigManager
from pylav.equalizers import EqualizerManager
from pylav.events import Event
from pylav.exceptions import AnotherClientAlreadyRegistered, CogAlreadyRegistered, CogHasBeenRegistered, NoNodeAvailable
from pylav.managed_node import LocalNodeManager
from pylav.node import Node
from pylav.node_manager import NodeManager
from pylav.player import Player
from pylav.player_manager import PlayerManager
from pylav.player_state import PlayerStateManager
from pylav.playlists import PlaylistManager
from pylav.query import Query
from pylav.utils import add_property

LOGGER = getLogger("red.PyLink.Client")

_COGS_REGISTERED = set()


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
    playlists: :class:`PlaylistManager`
        Represents the playlist manager that is used to save/load playlists.
    """

    _event_hooks = defaultdict(list)
    _config_manager: ConfigManager
    _equalizer_manager: EqualizerManager
    _player_state_manager: PlayerStateManager
    _playlist_manager: PlaylistManager
    _local_node_manager: LocalNodeManager
    _spotify_client_auth: ClientCredentialsFlow
    _spotify_client: SpotifyClient

    def __init__(
        self,
        bot: discord.Client,
        cog: Cog,
        player=Player,
        connect_back: bool = False,
        config_folder: aiopath.AsyncPath | pathlib.Path = CONFIG_DIR,
    ):
        global _COGS_REGISTERED
        if (istance := getattr(bot, "lavalink", None)) and not isinstance(istance, Client):
            raise AnotherClientAlreadyRegistered(
                f"Another client instance has already been registered to bot.lavalink with type: {type(istance)}"
            )
        if getattr(bot, "_pylav_client", None):
            if cog.__cog_name__ in _COGS_REGISTERED:
                raise CogAlreadyRegistered(f"{cog.__cog_name__} has already been registered!")
            elif cog.__cog_name__ not in _COGS_REGISTERED and _COGS_REGISTERED and getattr(self.bot, "pylav", None):
                _COGS_REGISTERED.add(cog.__cog_name__)
                raise CogHasBeenRegistered(f"Pylav is already loaded - {cog.__cog_name__} has been registered!")
        setattr(bot, "_pylav_client", self)
        add_property(bot, "lavalink", lambda self_: self_._pylav_client)  # noqa
        _COGS_REGISTERED.add(cog.__cog_name__)
        self._config_folder = aiopath.AsyncPath(config_folder)
        self._bot = bot
        self._user_id = str(bot.user.id)
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), json_serialize=ujson.dumps)
        self._node_manager = NodeManager(self)
        self._player_manager = PlayerManager(self, player)
        self._lib_config_manager = LibConfigManager(self)
        self._connect_back = connect_back
        self._warned_about_no_search_nodes = False
        self._ready = False

    @property
    def initialized(self) -> bool:
        """Returns whether the client has been initialized."""
        return self._ready

    @property
    def spotify_client(self) -> SpotifyClient:
        """Returns the spotify client."""
        return SpotifyClient(self._spotify_client_auth)

    async def initialize(self):
        if self._ready:
            return
        await self._lib_config_manager.initialize()
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
        self._config_folder = aiopath.AsyncPath(config_data.get("config_folder"))
        self._config_manager = ConfigManager(
            self, config_folder=self._config_folder, sql_connection_string=connection_string
        )
        await self._config_manager.initialize()

        self._equalizer_manager = EqualizerManager(
            self, config_folder=self._config_folder, sql_connection_string=connection_string
        )
        await self._equalizer_manager.initialize()

        self._player_state_manager = PlayerStateManager(
            self, config_folder=self._config_folder, sql_connection_string=connection_string
        )
        await self._player_state_manager.initialize()

        self._playlist_manager = PlaylistManager(
            self, config_folder=self._config_folder, sql_connection_string=connection_string
        )
        await self._playlist_manager.initialize()

        self._local_node_manager = LocalNodeManager(self, auto_update=auto_update_managed_nodes)

        # TODO: Uncomment and test

        if enable_managed_node:
            await self._local_node_manager.start(java_path=config_data.get("java_path"))
        from pylav.localfiles import LocalFile

        await LocalFile.add_root_folder(path=self._config_folder / "music", create=True)
        data = await self.config_manager.get_managed_node_config()
        spotify_data = data["extras"]["plugins"]["topissourcemanagers"]["spotify"]
        self._spotify_client_auth = ClientCredentialsFlow(
            client_id=spotify_data["clientId"], client_secret=spotify_data["clientSecret"]
        )
        await self.player_manager.restore_player_states()
        self._ready = True

    async def set_lib_config(
        self,
        config_folder: aiopath.AsyncPath | str,
        db_connection_string: str,
        java_path: str,
        enable_managed_node: bool,
        auto_update_managed_nodes: bool,
    ) -> dict:
        config_folder: aiopath.AsyncPath = aiopath.AsyncPath(config_folder)
        if await config_folder.is_file():
            raise ValueError("The config folder must be a directory.")
        if await config_folder.is_dir() and not await config_folder.exists():
            await config_folder.mkdir(parents=True, exist_ok=True)

        if db_connection_string.startswith("sqlite"):
            db_connection_string = "sqlite+aiosqlite:///"
        elif db_connection_string.startswith("postgresql"):
            if not db_connection_string.startswith("postgresql+asyncpg://"):
                raise ValueError(
                    "Postgresql connection string must be formatted like "
                    "`postgresql+asyncpg://user:password@host:port/dbname`."
                )
            else:
                LOGGER.debug("Postgresql connection string set to %s.", db_connection_string)
        else:
            raise ValueError("Invalid connection string, SQL or Postgresql connection string required.")

        self._config_folder = config_folder
        return await self._lib_config_manager.update_config(
            config_folder=str(config_folder),
            db_connection_string=db_connection_string,
            java_path=java_path,
            enable_managed_node=enable_managed_node,
            auto_update_managed_nodes=auto_update_managed_nodes,
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
    def config_folder(self) -> aiopath.AsyncPath:
        return self._config_folder

    @property
    def bot(self) -> discord.Client:
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
        resume_key: str = None,
        resume_timeout: int = 60,
        name: str = None,
        reconnect_attempts: int = 3,
        ssl: bool = False,
        search_only: bool = False,
        unique_identifier: str | None = None,
    ) -> Node:
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
        search_only: :class:`bool`
            Whether the node should only be used for searching. Defaults to `False`.
        unique_identifier: Optional[:class:`str`]
            A unique identifier for the node. Defaults to `None`.
        """

        return self.node_manager.add_node(
            host=host,
            port=port,
            password=password,
            resume_key=resume_key,
            resume_timeout=resume_timeout,
            name=name,
            reconnect_attempts=reconnect_attempts,
            ssl=ssl,
            search_only=search_only,
            unique_identifier=unique_identifier,
        )

    async def get_tracks(
        self, query: Query, node: Node = None, search_only_nodes: bool = False, first: bool = False
    ) -> dict:
        """|coro|
        Gets all tracks associated with the given query.

        Parameters
        ----------
        query: :class:`Query`
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
        :class:`dict`
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
            raise NoNodeAvailable("No available nodes!")
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
            raise NoNodeAvailable("No available nodes!")
        node = node or random.choice(self.node_manager.available_nodes)
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
            raise NoNodeAvailable("No available nodes!")
        node = node or random.choice(self.node_manager.available_nodes)
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

    async def unregister(self, cog: discord.ext.commands.Cog):
        """|coro|
        Unregister the specified Cog and if no cogs are left closes the client.

        Parameters
        ----------
        cog: :class:`discord.ext.commands.Cog`
            The cog to unregister.
        """
        global _COGS_REGISTERED
        _COGS_REGISTERED.discard(cog.__cog_name__)
        if not _COGS_REGISTERED:
            await self.player_manager.save_all_players()
            await self._config_manager.close()
            await self._equalizer_manager.close()
            await self._player_state_manager.close()
            await self._playlist_manager.close()
            await self._local_node_manager.shutdown()
            await self._lib_config_manager.close()
            await self._node_manager.close()
            await self._session.close()
            del self.bot._pylav_client  # noqa

    def get_player(self, guild: discord.Guild | int) -> Player:
        """|coro|
        Gets the player for the target guild.

        Parameters
        ----------
        guild: :class:`discord.Guild`
            The guild to get the player for.

        Returns
        -------
        :class:`Player`
            The player for the target guild.
        """
        if not isinstance(guild, int):
            guild = guild.id
        return self.player_manager.get(guild)

    async def connect_player(
        self,
        channel: discord.VoiceChannel,
        node: Node = None,
        self_deaf: bool = True,
    ) -> Player:
        """|coro|
        Connects the player for the target guild.

        Parameters
        ----------
        channel: :class:`discord.VoiceChannel`
            The channel to connect to.
        node: :class:`Node`
            The node to use for the connection.
        self_deaf: :class:`bool`
            Whether the bot should be deafened.

        Returns
        -------
        :class:`Player`
            The player for the target guild.
        """
        return await self.player_manager.create(channel, channel.rtc_region, node, self_deaf)

    async def construct_embed(
        self,
        *,
        embed: discord.Embed = None,
        colour: discord.Colour | int | None = None,
        color: discord.Colour | int | None = None,
        title: str = None,
        type: EmbedType = "rich",
        url: str = None,
        description: str = None,
        timestamp: datetime.datetime = None,
        author_name: str = None,
        author_url: str = None,
        thumbnail: str = None,
        footer: str = None,
        footer_url: str = None,
        messageable: Messageable = None,
    ) -> discord.Embed:

        if messageable and not (colour or color) and hasattr(self._bot, "get_embed_color"):
            colour = await self._bot.get_embed_color(messageable)
        elif colour or color:
            colour = colour or color

        contents = dict(title=title, type=type, url=url, description=description)
        if embed is not None:
            embed = embed.to_dict()
        else:
            embed = {}
        contents.update(embed)
        new_embed = discord.Embed.from_dict(contents)
        new_embed.color = colour
        if timestamp and isinstance(timestamp, datetime.datetime):
            new_embed.timestamp = timestamp
        else:
            new_embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)

        if footer:
            new_embed.set_footer(text=footer, icon_url=footer_url)
        if thumbnail:
            new_embed.set_thumbnail(url=thumbnail)
        if author_url or author_name:
            if author_url and author_name:
                new_embed.set_author(name=author_name, icon_url=author_url)
            elif author_name:
                new_embed.set_author(name=author_name)

        return new_embed
