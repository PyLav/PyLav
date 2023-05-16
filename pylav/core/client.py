from __future__ import annotations

import asyncio
import contextlib
import datetime
import itertools
import operator
import os
import pathlib
import random
import sys
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from types import MethodType
from typing import Any

import aiohttp
import aiohttp_client_cache
import aiopath
import discord
import discord.ext.commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asyncspotify import Client as SpotifyClient
from asyncspotify import ClientCredentialsFlow
from discord.abc import Messageable
from discord.ext.commands import Context
from discord.types.embed import EmbedType
from packaging.version import Version

from pylav import VERSION

# noinspection PyProtectedMember
from pylav._internals.functions import add_property
from pylav.compat import json
from pylav.constants import MAX_RECURSION_DEPTH
from pylav.constants.config import (
    CONFIG_DIR,
    EXTERNAL_UNMANAGED_HOST,
    EXTERNAL_UNMANAGED_PASSWORD,
    EXTERNAL_UNMANAGED_PORT,
    EXTERNAL_UNMANAGED_SSL,
    IN_CONTAINER,
    JAVA_EXECUTABLE,
    LOCAL_TRACKS_FOLDER,
    MANAGED_NODE_APPLE_MUSIC_API_KEY,
    MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE,
    MANAGED_NODE_DEEZER_KEY,
    MANAGED_NODE_SPOTIFY_CLIENT_ID,
    MANAGED_NODE_SPOTIFY_CLIENT_SECRET,
    MANAGED_NODE_SPOTIFY_COUNTRY_CODE,
    MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN,
    POSTGRES_CONNECTIONS,
    REDIS_FULL_ADDRESS_RESPONSE_CACHE,
    TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS,
    TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS,
    TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS,
    overrides,
)
from pylav.constants.playlists import BUNDLED_DEEZER_PLAYLIST_IDS, BUNDLED_PLAYLIST_IDS, BUNDLED_SPOTIFY_PLAYLIST_IDS
from pylav.core.bot_overrides import get_context, process_commands
from pylav.core.context import PyLavContext
from pylav.events.base import PyLavEvent
from pylav.events.manager import DispatchManager
from pylav.exceptions.client import AnotherClientAlreadyRegisteredException, PyLavInvalidArgumentsException
from pylav.exceptions.node import NoNodeAvailableException, NoNodeWithRequestFunctionalityAvailableException
from pylav.exceptions.request import HTTPException
from pylav.extension.bundled_node import LAVALINK_DOWNLOAD_DIR
from pylav.extension.bundled_node.manager import LocalNodeManager
from pylav.extension.flowery.base import FloweryAPI
from pylav.extension.m3u import M3UParser
from pylav.extension.radio import RadioBrowser
from pylav.helpers.singleton import SingletonCallable, SingletonClass
from pylav.helpers.time import get_now_utc, get_tz_utc
from pylav.logging import getLogger
from pylav.nodes.api.responses import rest_api
from pylav.nodes.api.responses.route_planner import Status as RoutePlannerStatus
from pylav.nodes.api.responses.track import Track as Track_namespace_conflict
from pylav.nodes.manager import NodeManager
from pylav.nodes.node import Node
from pylav.players.manager import PlayerController
from pylav.players.player import Player
from pylav.players.query.obj import Query
from pylav.players.tracks.decoder import decode_track
from pylav.players.tracks.obj import Track
from pylav.storage.controllers.config import ConfigController
from pylav.storage.controllers.equalizers import EqualizerController
from pylav.storage.controllers.migrator import MigrationController
from pylav.storage.controllers.nodes import NodeController
from pylav.storage.controllers.players.config import PlayerConfigController
from pylav.storage.controllers.players.states import PlayerStateController
from pylav.storage.controllers.playlists import PlaylistController
from pylav.storage.controllers.queries import QueryController
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.misc import DATABASE_ENGINE, IS_POSTGRES
from pylav.storage.models.config import Config
from pylav.storage.models.equilizer import Equalizer
from pylav.storage.models.node.real import Node as Node_namespace_conflict
from pylav.storage.models.player.state import PlayerState
from pylav.type_hints.bot import DISCORD_BOT_TYPE, DISCORD_COG_TYPE, DISCORD_CONTEXT_TYPE, DISCORD_INTERACTION_TYPE
from pylav.utils.aiohttp_postgres_cache import PostgresCacheBackend
from pylav.utils.localtracks import LocalTrackCache

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLav", pathlib.Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


LOGGER = getLogger("PyLav.Client")


class Client(metaclass=SingletonClass):
    """
    Represents a Lavalink client used to manage nodes and connections.

    .. _event loop: https://docs.python.org/3/library/asyncio-eventloop.html

    Parameters
    ----------
    bot : :class:`DISCORD_BOT_TYPE`
        The bot instance.
    cog: :class:`DISCORD_COG_TYPE`
        The cog to register the client to.
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
    config_folder: Optional[:class:`pathlib.Path`]
        The path to the settings folder. Defaults to ``CONFIG_DIR``.
    """

    _local_node_manager: LocalNodeManager
    _asyncio_lock = asyncio.Lock()
    _config: Config
    __cogs_registered = set()
    __old_process_command_method: Callable = None
    __old_get_context: Callable = None
    _initiated = False
    __local_tracks_cache: LocalTrackCache

    def __init__(
        self,
        bot: DISCORD_BOT_TYPE,
        cog: DISCORD_COG_TYPE,
        player: type[Player] = Player,  # type: ignore
        connect_back: bool = False,
        config_folder: aiopath.AsyncPath | pathlib.Path = CONFIG_DIR,
    ):
        try:
            setattr(bot, "_pylav_client", self)
            # noinspection PyProtectedMember
            add_property(bot, "lavalink", lambda b: b._pylav_client)
            # noinspection PyProtectedMember
            add_property(bot, "pylav", lambda b: b._pylav_client)
            if self.__old_process_command_method is None:
                self.__old_process_command_method = bot.process_commands
            if self.__old_get_context is None:
                self.__old_get_context = bot.get_context
            self._disable_translations = False
            self._context_translator: Callable[[DISCORD_BOT_TYPE, discord.Guild], Awaitable[None]] | None = None
            self.ready = asyncio.Event()
            bot.process_commands = MethodType(process_commands, bot)
            bot.get_context = MethodType(get_context, bot)
            self.__cogs_registered.add(cog.__cog_name__)
            config_folder = pathlib.Path(config_folder)
            (config_folder / ".data").mkdir(exist_ok=True, parents=True)
            self._config_folder = aiopath.AsyncPath(config_folder)
            self._bot = bot
            self._user_id = str(bot.user.id)
            if REDIS_FULL_ADDRESS_RESPONSE_CACHE:
                self._aiohttp_client_cache = aiohttp_client_cache.RedisBackend(
                    address=REDIS_FULL_ADDRESS_RESPONSE_CACHE,
                    cache_control=True,
                    allowed_codes=(200,),
                    allowed_methods=("GET",),
                    include_headers=True,
                    expire_after=datetime.timedelta(days=1),
                    timeout=2.5,
                    ignored_params=["auth_token", "timestamp"],
                )
            else:
                self._aiohttp_client_cache = PostgresCacheBackend(
                    cache_control=True,
                    allowed_codes=(200,),
                    allowed_methods=("GET",),
                    include_headers=True,
                    ignored_params=["auth_token", "timestamp"],
                    expire_after=datetime.timedelta(days=1),
                    timeout=2.5,
                )
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), json_serialize=json.dumps)
            self._cached_session = aiohttp_client_cache.CachedSession(
                timeout=aiohttp.ClientTimeout(total=30), json_serialize=json.dumps, cache=self._aiohttp_client_cache
            )
            # Attach the Client to the necessary objects
            CachedModel.attach_client(self)
            Query.attach_client(self)
            Track.attach_client(self)
            PlayerState.attach_client(self)
            Equalizer.attach_client(self)

            self._node_manager = NodeManager(
                self,
                external_host=EXTERNAL_UNMANAGED_HOST,
                external_port=EXTERNAL_UNMANAGED_PORT,
                external_password=EXTERNAL_UNMANAGED_PASSWORD,
                external_ssl=EXTERNAL_UNMANAGED_SSL,
            )
            self._player_manager = PlayerController(self, player)
            self._lib_config_manager = ConfigController(self)
            self._node_config_manager = NodeController(self)
            self._playlist_config_manager = PlaylistController(self)
            self._query_cache_manager = QueryController(self)
            self._update_schema_manager = MigrationController(self)
            self._dispatch_manager = DispatchManager(self)
            self._player_state_db_manager = PlayerStateController(self)
            self._player_config_manager = PlayerConfigController(self)
            self._equalizer_config_manager = EqualizerController(self)

            self._flowery_api = FloweryAPI(self)
            self._radio_manager = RadioBrowser(self)
            self._m3u8parser = M3UParser(self)
            self._connect_back = connect_back
            self._warned_about_no_search_nodes = False
            self._spotify_client_id = None
            self._spotify_client_secret = None
            self._spotify_auth = None
            self._shutting_down = False
            self._scheduler = AsyncIOScheduler(prefix="pylav_scheduler.")
            self._scheduler.configure(timezone=get_tz_utc())
            self._wait_for_playlists = asyncio.Event()
            self._wait_for_playlists.set()
        except Exception:
            LOGGER.exception("Failed to initialize Lavalink")
            raise

    async def set_context_locale(self, guild: discord.Guild | None) -> None:
        """Set the locale for the current context."""
        if self._disable_translations:
            return
        try:
            if self._context_translator is None:
                from redbot.core.i18n import set_contextual_locales_from_guild

                self._context_translator = set_contextual_locales_from_guild
            await self._context_translator(self.bot, guild)
        except Exception:  # noqa
            self._disable_translations = True

    async def on_pylav_red_api_tokens_update(self, service_name: str, api_tokens: dict[str, str]) -> None:
        """Update API tokens for services when they are updated in Red."""
        match service_name:
            case "spotify" if "client_id" in api_tokens and "client_secret" in api_tokens:
                await self.update_spotify_tokens(**api_tokens)
            case "apple_music" if "token" in api_tokens and "country_code" in api_tokens:
                await self.update_applemusic_tokens(**api_tokens)
            case "deezer" if "master_token" in api_tokens:
                await self.update_deezer_tokens(**api_tokens)
            case "yandexmusic" if "token" in api_tokens:
                await self.update_yandex_tokens(**api_tokens)
            case "google" if ("email" in api_tokens and "password" in api_tokens):
                await self.update_google_account(**api_tokens)

    async def on_pylav_shard_resumed(self, shard_id: int) -> None:
        """Handle shard resume events."""
        if self._shutting_down or not self.initialized:
            return
        LOGGER.debug("Shard %s resumed, checking for affected players", shard_id)
        players = filter(lambda p: p.guild.shard_id == shard_id, self.player_manager.players.copy().values())
        for player in players:
            await self.set_context_locale(player.guild)
            await player.reconnect()

    async def on_pylav_shard_ready(self, shard_id: int) -> None:
        """Handle shard ready events."""
        if self._shutting_down or not self.initialized:
            return
        LOGGER.debug("Shard %s ready, checking for affected players", shard_id)
        players = filter(lambda p: p.guild.shard_id == shard_id, self.player_manager.players.copy().values())
        for player in players:
            await self.set_context_locale(player.guild)
            await player.reconnect()

    async def on_pylav_resumed(self) -> None:
        """Handle resume events."""
        if self._shutting_down or not self.initialized:
            return
        LOGGER.debug("Resumed, checking for affected players")

        for player in self.player_manager.players.values():
            await self.set_context_locale(player.guild)
            await player.reconnect()

    async def on_pylav_ready(self) -> None:
        """Handle ready events."""
        if self._shutting_down or not self.initialized:
            return
        LOGGER.debug("Ready, checking for affected players")
        for player in self.player_manager.players.values():
            await self.set_context_locale(player.guild)
            await player.reconnect()

    async def wait_until_ready(self, timeout: float | None = None) -> None:
        """Wait until the client is ready to use."""
        await asyncio.wait_for(self.ready.wait(), timeout=timeout)

    @property
    def initialized(self) -> bool:
        """Returns whether the client has been initialized"""
        return self._initiated

    @property
    def scheduler(self) -> AsyncIOScheduler:
        """Returns the scheduler"""
        return self._scheduler

    @property
    def radio_browser(self) -> RadioBrowser:
        """Returns the radio browser instance"""
        return self._radio_manager

    @property
    def dispatch_manager(self) -> DispatchManager:
        """Returns the dispatch manager"""
        return self._dispatch_manager

    @property
    def player_config_manager(self) -> PlayerConfigController:
        """Returns the player config manager"""
        return self._player_config_manager

    @property
    def spotify_client(self) -> SpotifyClient | None:
        """Returns the spotify client"""
        return SpotifyClient(self._spotify_auth) if self._spotify_auth else None

    @property
    def is_shutting_down(self) -> bool:
        """Returns whether the client is shutting down"""
        return self._shutting_down

    @property
    def node_db_manager(self) -> NodeController:
        """Returns the sql node config manager"""
        return self._node_config_manager

    @property
    def player_state_db_manager(self) -> PlayerStateController:
        """Returns the sql player state config manager"""
        return self._player_state_db_manager

    @property
    def playlist_db_manager(self) -> PlaylistController:
        """Returns the sql playlist config manager"""
        return self._playlist_config_manager

    @property
    def equalizer_db_manager(self) -> EqualizerController:
        """Returns the sql equalizer config manager"""
        return self._equalizer_config_manager

    @property
    def flowery_api(self) -> FloweryAPI:
        """Returns the flowery api"""
        return self._flowery_api

    @property
    def lib_db_manager(self) -> ConfigController:
        """Returns the sql lib config manager"""
        return self._lib_config_manager

    @property
    def query_cache_manager(self) -> QueryController:
        """Returns the query cache manager"""
        return self._query_cache_manager

    @property
    def managed_node_controller(self) -> LocalNodeManager:
        """Returns the local node manager"""
        return self._local_node_manager

    @property
    def node_manager(self) -> NodeManager:
        """Returns the node manager"""
        return self._node_manager

    @property
    def player_manager(self) -> PlayerController:
        """Returns the player manager"""
        return self._player_manager

    @property
    def config_folder(self) -> aiopath.AsyncPath:
        """Returns the config folder"""
        return self._config_folder

    @property
    def bot(self) -> DISCORD_BOT_TYPE:
        """Returns the bot client"""
        return self._bot

    @property
    def session(self) -> aiohttp.ClientSession:
        """Returns the aiohttp session used by the PyLav client"""
        return self._session

    @property
    def cached_session(self) -> aiohttp_client_cache.CachedSession:
        """Returns the cached aiohttp session used by the PyLav client"""
        return self._cached_session

    @property
    def lib_version(self) -> Version:
        """Returns the version of the PyLav library"""
        return VERSION

    @property
    def bot_id(self) -> str:
        """Returns the bot id"""
        return self._user_id

    @property
    def local_tracks_cache(self) -> LocalTrackCache:
        """Returns the local tracks cache"""
        return self.__local_tracks_cache

    @SingletonCallable.run_once_async
    async def initialize(self) -> None:
        """Initialize the client"""
        try:
            if not self._initiated:
                await self._maybe_start_pylav()
        except Exception as exc:
            LOGGER.critical("Failed start up", exc_info=exc)
            raise exc

    async def _maybe_start_pylav(self):
        async with self._asyncio_lock:
            if not self._initiated:
                self._initiated = True
                self.ready.clear()
                await self._wait_until_ready()
                if IS_POSTGRES:
                    await DATABASE_ENGINE.start_connection_pool(max_size=POSTGRES_CONNECTIONS)
                (
                    spotify_client_id,
                    spotify_client_secret,
                    deezer_token,
                    yandex_access_token,
                    apple_music_token,
                ) = await self._get_service_tokens()

                self.bot.add_listener(self.on_pylav_red_api_tokens_update, name="on_red_api_tokens_update")
                if isinstance(self.bot, discord.AutoShardedClient):
                    self.bot.add_listener(self.on_pylav_shard_ready, name="on_shard_ready")
                else:
                    self.bot.add_listener(self.on_pylav_ready, name="on_ready")
                await self._initialise_modules()
                await self._config.update_config_folder(CONFIG_DIR)
                config_data = await self._config.fetch_all()
                java_path = config_data["java_path"]
                config_folder = config_data["config_folder"]
                localtrack_folder = await self.update_localtracks_folder(folder=config_data["localtrack_folder"])
                if java_path != JAVA_EXECUTABLE and os.path.exists(JAVA_EXECUTABLE):
                    await self._config.update_java_path(JAVA_EXECUTABLE)
                LOGGER.info("Lavalink folder: %s", LAVALINK_DOWNLOAD_DIR)
                LOGGER.info("Settings folder: %s", config_folder)
                LOGGER.info("Localtracks folder: %s", localtrack_folder)
                self._config_folder = aiopath.AsyncPath(config_folder)
                self.__local_tracks_cache = LocalTrackCache(self, localtrack_folder)
                bundled_node_config = self._node_config_manager.bundled_node_config()
                spotify_client_id, spotify_client_secret = await self._initialize_yaml_config(
                    bundled_node_config,
                    spotify_client_id,
                    spotify_client_secret,
                    deezer_token,
                    yandex_access_token,
                    apple_music_token,
                )
                self._has_deezer_support = True
                self._has_apm_support = True
                self._has_spotify_support = False
                self._has_yandex_support = False

                if spotify_client_id and spotify_client_secret:
                    self._spotify_auth = ClientCredentialsFlow(
                        client_id=spotify_client_id, client_secret=spotify_client_secret
                    )
                    self._has_spotify_support = True
                    await self.update_spotify_tokens(client_id=spotify_client_id, client_secret=spotify_client_secret)
                if yandex_access_token:
                    self._has_yandex_support = True
                    await self.update_yandex_tokens(token=yandex_access_token)
                if apple_music_token:
                    await self.update_applemusic_tokens(
                        token=apple_music_token, country_code=MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE
                    )
                await self._run_post_init_jobs(java_path)
                self.ready.set()
                LOGGER.info("PyLav is ready")
                await self.__local_tracks_cache.initialize()

    async def _initialise_modules(self):
        await self._lib_config_manager.initialize()
        self._config = self._lib_config_manager.get_config()
        await Node_namespace_conflict.create_managed(identifier=self.bot.user.id)
        await self._update_schema_manager.run_updates()
        await self._radio_manager.initialize()
        await self._player_manager.initialize()
        await self.player_config_manager.initialize_global_config()

    async def managed_node_is_enabled(self) -> bool:
        """Returns whether the managed node is enabled or not"""
        if IN_CONTAINER:
            return False
        return (
            False
            if (self._node_manager._unmanaged_external_password and self._node_manager._unmanaged_external_host)
            else await self.lib_db_manager.get_config().fetch_enable_managed_node()
        )

    async def _run_post_init_jobs(self, java_path) -> None:
        self._user_id = str(self._bot.user.id)
        self._local_node_manager = LocalNodeManager(self)
        enable_managed_node = await self.managed_node_is_enabled()
        if IN_CONTAINER:
            LOGGER.warning("Running in container, disabling managed node")
        time_now = get_now_utc()
        await self._maybe_start_bundled_node(enable_managed_node, java_path)
        await self.node_manager.connect_to_all_nodes()
        await self.node_manager.wait_until_ready()
        await self._maybe_wait_until_bundled_node(enable_managed_node)
        await self._update_schema_manager.run_deferred_tasks_which_depend_on_node()
        await self._maybe_update_next_execution_bundled_playlist(time_now)
        await self._maybe_update_next_execution_bundled_external_playlists(time_now)
        await self._maybe_update_next_execution_external_playlists(time_now)
        await self._maybe_force_update_bundled_playlists()
        await self._add_scheduler_job_cache_cleanup()
        await self._add_scheduler_job_bundled_playlist()
        await self._add_scheduler_job_bundled_external_playlists()
        await self._add_scheduler_job_external_playlists()
        self._scheduler.start()
        await self.player_manager.restore_player_states()

    async def _maybe_start_bundled_node(self, enable_managed_node: bool, java_path: str) -> None:
        # noinspection PyProtectedMember
        if enable_managed_node:
            await self._local_node_manager.start(java_path=java_path)
        else:
            self._local_node_manager.ready.set()

    async def _maybe_force_update_bundled_playlists(self) -> None:
        total_bundled_playlists = len(BUNDLED_PLAYLIST_IDS)
        if not self._has_deezer_support:
            total_bundled_playlists -= len(BUNDLED_DEEZER_PLAYLIST_IDS)
        if not self._has_spotify_support:
            total_bundled_playlists -= len(BUNDLED_SPOTIFY_PLAYLIST_IDS)

        if await self.playlist_db_manager.count() < total_bundled_playlists:
            time_now = get_now_utc()
            self._wait_for_playlists.clear()
            await self._config.update_next_execution_update_bundled_playlists(time_now - datetime.timedelta(days=7))
            await self._config.update_next_execution_update_bundled_external_playlists(
                time_now - datetime.timedelta(days=7)
            )

    async def _maybe_wait_until_bundled_node(self, enable_managed_node):
        # noinspection PyProtectedMember
        if enable_managed_node:
            await self._local_node_manager.wait_until_connected()

    async def _wait_until_ready(self):
        if hasattr(self.bot, "wait_until_red_ready"):
            LOGGER.debug("Running on a Red bot, waiting for Red to be ready")
            await self.bot.wait_until_red_ready()
        else:
            LOGGER.debug("Running a discord.py bot waiting for bot to be ready")
            await self.bot.wait_until_ready()

    async def _get_service_tokens(self):
        if hasattr(self.bot, "get_shared_api_tokens") and callable(getattr(self.bot, "get_shared_api_tokens")):
            spotify = await self.bot.get_shared_api_tokens("spotify")
            client_id = spotify.get("client_id")
            client_secret = spotify.get("client_secret")
            if client_id and client_secret:
                LOGGER.debug("Existing Spotify tokens found; Using clientID - %s", client_id)
            else:
                client_id = MANAGED_NODE_SPOTIFY_CLIENT_ID
                client_secret = MANAGED_NODE_SPOTIFY_CLIENT_SECRET
            deezer = await self.bot.get_shared_api_tokens("deezer")
            deezer_token = deezer.get("master_token")
            if deezer_token:
                LOGGER.debug("Existing Deezer token found; Using it")
            else:
                deezer_token = MANAGED_NODE_DEEZER_KEY

            yandex = await self.bot.get_shared_api_tokens("yandexmusic")
            yandex_access_token = yandex.get("token")
            if yandex_access_token:
                LOGGER.debug("Existing Yandex Music token found; Using it")
            else:
                yandex_access_token = MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN

            apple_music = await self.bot.get_shared_api_tokens("apple_music")
            apple_music_token = apple_music.get("token")
            if apple_music_token:
                LOGGER.debug("Existing Apple Music token found; Using it")
            else:
                apple_music_token = MANAGED_NODE_APPLE_MUSIC_API_KEY
        else:
            LOGGER.info("PyLav being run from a non Red bot")
            client_id = MANAGED_NODE_SPOTIFY_CLIENT_ID
            client_secret = MANAGED_NODE_SPOTIFY_CLIENT_SECRET
            deezer_token = MANAGED_NODE_DEEZER_KEY
            yandex_access_token = MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN
            apple_music_token = MANAGED_NODE_APPLE_MUSIC_API_KEY

        return client_id, client_secret, deezer_token, yandex_access_token, apple_music_token

    async def _add_scheduler_job_external_playlists(self):
        next_execution_update_external_playlists = await self._config.fetch_next_execution_update_external_playlists()
        if next_execution_update_external_playlists >= (
            alt_next := (get_now_utc() + datetime.timedelta(days=TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS))
        ):
            next_execution_update_external_playlists = alt_next
        self._scheduler.add_job(
            self.playlist_db_manager.update_external_playlists,
            trigger="interval",
            days=TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS,
            max_instances=1,
            next_run_time=next_execution_update_external_playlists,
            replace_existing=True,
            name="update_external_playlists",
            coalesce=True,
            id=f"{self.bot.user.id}-update_external_playlists",
            misfire_grace_time=None,  # type: ignore
        )
        LOGGER.info(
            "Scheduling next run of External Playlist update task to: %s",
            next_execution_update_external_playlists,
        )

    async def _add_scheduler_job_bundled_external_playlists(self):
        next_execution_update_bundled_external_playlists = (
            await self._config.fetch_next_execution_update_bundled_external_playlists()
        )
        if next_execution_update_bundled_external_playlists >= (
            alt_next := (get_now_utc() + datetime.timedelta(days=TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS))
        ):
            next_execution_update_bundled_external_playlists = alt_next
        self._scheduler.add_job(
            self.playlist_db_manager.update_bundled_external_playlists,
            trigger="interval",
            days=TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS,
            max_instances=1,
            next_run_time=next_execution_update_bundled_external_playlists,
            replace_existing=True,
            name="update_bundled_external_playlists",
            coalesce=True,
            id=f"{self.bot.user.id}-update_bundled_external_playlists",
            misfire_grace_time=None,  # type: ignore
        )
        LOGGER.info(
            "Scheduling next run of Bundled External Playlist update task to: %s",
            next_execution_update_bundled_external_playlists,
        )

    async def _add_scheduler_job_bundled_playlist(self):
        next_execution_update_bundled_playlists = await self._config.fetch_next_execution_update_bundled_playlists()
        if next_execution_update_bundled_playlists >= (
            alt_next := (get_now_utc() + datetime.timedelta(days=TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS))
        ):
            next_execution_update_bundled_playlists = alt_next
        self._scheduler.add_job(
            self.playlist_db_manager.update_bundled_playlists,
            trigger="interval",
            days=TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS,
            max_instances=1,
            next_run_time=next_execution_update_bundled_playlists,
            replace_existing=True,
            name="update_bundled_playlists",
            coalesce=True,
            id=f"{self.bot.user.id}-update_bundled_playlists",
            misfire_grace_time=None,  # type: ignore
        )
        LOGGER.info(
            "Scheduling next run of Bundled Playlist update task to: %s",
            next_execution_update_bundled_playlists,
        )

    async def _add_scheduler_job_cache_cleanup(self):
        self._scheduler.add_job(
            self._query_cache_manager.delete_old,
            trigger="interval",
            seconds=600,
            max_instances=1,
            replace_existing=True,
            name="cache_delete_old",
            coalesce=True,
            id=f"{self.bot.user.id}-cache_delete_old",
        )

    async def _maybe_update_next_execution_external_playlists(self, time_now):
        if await self._config.fetch_next_execution_update_external_playlists() is None:
            await self._config.update_next_execution_update_external_playlists(
                time_now + datetime.timedelta(minutes=30)
            )

    async def _maybe_update_next_execution_bundled_external_playlists(self, time_now):
        if await self._config.fetch_next_execution_update_bundled_external_playlists() is None:
            await self._config.update_next_execution_update_bundled_external_playlists(
                time_now + datetime.timedelta(minutes=10, days=7)
            )

    async def _maybe_update_next_execution_bundled_playlist(self, time_now):
        if await self._config.fetch_next_execution_update_bundled_playlists() is None:
            await self._config.update_next_execution_update_bundled_playlists(
                time_now + datetime.timedelta(minutes=5, days=1)
            )

    @staticmethod
    async def _initialize_yaml_config(
        bundled_node_config,
        spotify_client_id,
        spotify_client_secret,
        deezer_token,
        yandex_access_token,
        apple_music_token,
    ):
        yaml_data = await bundled_node_config.fetch_yaml()
        need_update = False
        if not all([spotify_client_id, spotify_client_secret]):
            yaml_data["plugins"]["lavasrc"]["sources"]["spotify"] = False
            need_update = True
        elif all([spotify_client_id, spotify_client_secret]):
            yaml_data["plugins"]["lavasrc"]["spotify"]["clientId"] = spotify_client_id
            yaml_data["plugins"]["lavasrc"]["spotify"]["clientSecret"] = spotify_client_secret
            yaml_data["plugins"]["lavasrc"]["sources"]["spotify"] = True
            need_update = True
        if deezer_token:
            yaml_data["plugins"]["lavasrc"]["deezer"]["masterDecryptionKey"] = deezer_token
            yaml_data["plugins"]["lavasrc"]["sources"]["deezer"] = True
            need_update = True
        if yandex_access_token:
            yaml_data["plugins"]["lavasrc"]["yandexmusic"]["accessToken"] = yandex_access_token
            yaml_data["plugins"]["lavasrc"]["sources"]["yandexmusic"] = True
            need_update = True
        if apple_music_token:
            yaml_data["plugins"]["lavasrc"]["applemusic"]["mediaAPIToken"] = apple_music_token
            yaml_data["plugins"]["lavasrc"]["sources"]["applemusic"] = True
        if need_update:
            await bundled_node_config.update_yaml(yaml_data)
        return spotify_client_id, spotify_client_secret

    async def register(self, cog: DISCORD_COG_TYPE) -> None:
        """Register a cog to the PyLav Client."""
        LOGGER.debug("Registering cog %s", cog.__cog_name__)
        if (instance := getattr(self.bot, "pylav", None)) and not isinstance(instance, Client):
            raise AnotherClientAlreadyRegisteredException(
                f"Another client instance has already been registered to bot.pylav with type: {type(instance)}"
            )
        self.__cogs_registered.add(cog.__cog_name__)

    async def update_spotify_tokens(self, client_id: str, client_secret: str, **kwargs) -> None:
        """Update Spotify tokens for the managed node and the client instance."""
        LOGGER.info("Updating Spotify Tokens")
        LOGGER.debug("New Spotify token: ClientId: %s || ClientSecret: %s", client_id, client_secret)
        self._spotify_auth = ClientCredentialsFlow(client_id=client_id, client_secret=client_secret)
        bundled_node_config = self._node_config_manager.bundled_node_config()
        bundled_node_config_yaml = await bundled_node_config.fetch_yaml()
        bundled_node_config_yaml["plugins"]["lavasrc"]["sources"]["spotify"] = True
        bundled_node_config_yaml["plugins"]["lavasrc"]["spotify"]["clientId"] = client_id
        bundled_node_config_yaml["plugins"]["lavasrc"]["spotify"]["clientSecret"] = client_secret
        bundled_node_config_yaml["plugins"]["lavasrc"]["spotify"]["countryCode"] = kwargs.get(
            "country_code", MANAGED_NODE_SPOTIFY_COUNTRY_CODE
        )
        await bundled_node_config.update_yaml(bundled_node_config_yaml)

    async def update_deezer_tokens(self, master_token: str, **kwargs: Any) -> None:
        """Update Deezer tokens for the managed node."""
        LOGGER.info("Updating Deezer Tokens")
        LOGGER.debug("New Deezer token: %s", master_token)
        bundled_node_config = self._node_config_manager.bundled_node_config()
        bundled_node_config_yaml = await bundled_node_config.fetch_yaml()
        bundled_node_config_yaml["plugins"]["lavasrc"]["sources"]["deezer"] = True
        bundled_node_config_yaml["plugins"]["lavasrc"]["deezer"]["masterDecryptionKey"] = master_token
        await bundled_node_config.update_yaml(bundled_node_config_yaml)

    async def update_yandex_tokens(self, token: str, **kwargs: Any) -> None:
        """Update Yandex tokens for the managed node."""
        LOGGER.info("Updating Yandex Tokens")
        LOGGER.debug("New Yandex token: %s", token)
        bundled_node_config = self._node_config_manager.bundled_node_config()
        bundled_node_config_yaml = await bundled_node_config.fetch_yaml()
        bundled_node_config_yaml["plugins"]["lavasrc"]["sources"]["yandexmusic"] = True
        bundled_node_config_yaml["plugins"]["lavasrc"]["yandexmusic"]["accessToken"] = token
        await bundled_node_config.update_yaml(bundled_node_config_yaml)

    async def update_applemusic_tokens(self, token: str, country_code: str, **kwargs: Any) -> None:
        """Update Apple Music tokens for the managed node."""
        LOGGER.info("Updating Apple Music Tokens")
        LOGGER.debug("New Apple Music tokens: mediaAPIToken %s || countryCode %s", token, country_code)
        bundled_node_config = self._node_config_manager.bundled_node_config()
        bundled_node_config_yaml = await bundled_node_config.fetch_yaml()
        bundled_node_config_yaml["plugins"]["lavasrc"]["sources"]["applemusic"] = True
        bundled_node_config_yaml["plugins"]["lavasrc"]["applemusic"]["mediaAPIToken"] = token
        bundled_node_config_yaml["plugins"]["lavasrc"]["applemusic"]["countryCode"] = kwargs.get(
            "country_code", MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE
        )
        await bundled_node_config.update_yaml(bundled_node_config_yaml)

    async def update_google_account(self, email: str, password: str, **kwargs: Any) -> None:
        """Update Google Account for the managed node."""
        LOGGER.info("Updating Google Account")
        LOGGER.debug("New Google Account: %s", email)
        bundled_node_config = self._node_config_manager.bundled_node_config()
        bundled_node_config_yaml = await bundled_node_config.fetch_yaml()
        bundled_node_config_yaml["lavalink"]["server"]["youtubeConfig"]["email"] = email
        bundled_node_config_yaml["lavalink"]["server"]["youtubeConfig"]["password"] = password
        await bundled_node_config.update_yaml(bundled_node_config_yaml)

    async def add_node(
        self,
        *,
        unique_identifier: int,
        host: str,
        port: int,
        password: str,
        resume_timeout: int = 60,
        name: str = None,
        reconnect_attempts: int = -1,
        ssl: bool = False,
        search_only: bool = False,
        managed: bool = False,
        yaml: dict | None = None,
        disabled_sources: list[str] = None,
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
            An identifier for the node that will show in logs. Defaults to `None`
        reconnect_attempts: Optional[:class:`int`]
            The amount of times connection with the node will be reattempted before giving up.
            Set to `-1` for infinite. Defaults to `3`.
        ssl: Optional[:class:`bool`]
            Whether to use SSL for the connection. Defaults to `False`.
        search_only: :class:`bool`
            Whether the node should only be used for searching. Defaults to `False`.
        unique_identifier: :class:`in`
            A unique identifier for the node. Defaults to `None`.
        yaml: Optional[:class:`dict`]
            A dictionary of extra information to be stored in the node. Defaults to `None`.
        extras: Optional[:class:`dict`]
            A dictionary of extra information to be stored in the node. Defaults to `None`.
        managed: :class:`bool`
            Whether the node is managed by the client. Defaults to `False`.
        disabled_sources: Optional[:class:`list`[:class:`str`]]
            A list of sources that should be disabled for the node. Defaults to `None`.
        temporary: :class:`bool`
            Whether the node is temporary. Defaults to `False`.
        """
        return await self.node_manager.add_node(
            host=host,
            port=port,
            password=password,
            resume_timeout=resume_timeout,
            name=name,
            reconnect_attempts=reconnect_attempts,
            ssl=ssl,
            search_only=search_only,
            unique_identifier=unique_identifier,
            managed=managed,
            yaml=yaml,
            disabled_sources=disabled_sources,
            extras=extras or {},
            temporary=temporary,
        )

    async def decode_track(
        self, track: str, feature: str = None, raise_on_failure: bool = False, lazy: bool = False
    ) -> Track_namespace_conflict | HTTPException:
        """|coro|
        Decodes a base64-encoded track string into a dict.

        Parameters
        ----------
        track: :class:`str`
            The base64-encoded `track` string.
        feature: Optional[:class:`str`]
            The feature to decode the track for. Defaults to `None`.
        raise_on_failure: Optional[:class:`bool`]
            Whether to raise an exception if the track fails to decode. Defaults to `False`.
        lazy: :class:`bool`
            Weather to decode within the Bot or send to Lavalink. Defaults to `False`.

        Returns
        -------
        LavalinkTrackObject
            An object representing the track's information.
        """
        if lazy:
            with contextlib.suppress(Exception):
                return decode_track(track)
        if not self.node_manager.available_nodes:
            raise NoNodeAvailableException(_("There are no available nodes!"))
        node = await self.node_manager.find_best_node(feature=feature)
        if node is None and feature:
            raise NoNodeWithRequestFunctionalityAvailableException(
                _("No node with {feature_name_variable_do_not_translate} functionality available!").format(
                    feature_name_variable_do_not_translate=feature
                ),
                feature=feature,
            )
        try:
            response = await node.fetch_decodetrack(track, raise_on_failure=raise_on_failure)
            if isinstance(response, Track_namespace_conflict):
                return response
            raise TypeError
        except Exception as exc:  # noqa
            return decode_track(track)

    async def decode_tracks(
        self, tracks: list, feature: str = None, raise_on_failure: bool = False
    ) -> list[Track_namespace_conflict]:
        """|coro|
        Decodes a list of base64-encoded track strings into a dict.

        Parameters
        ----------
        tracks: list[:class:`str`]
            A list of base64-encoded `track` strings.
        feature: Optional[:class:`str`]
            The feature to decode the tracks for. Defaults to `None`.
        raise_on_failure: Optional[:class:`bool`]
            Whether to raise an exception if the tracks fail to decode. Defaults to `False`.

        Returns
        -------
        List[LavalinkTrackObject]
            A list of LavalinkTrackObject representing track information.
        """
        if not self.node_manager.available_nodes:
            raise NoNodeAvailableException(_("There are no available nodes!"))
        node = await self.node_manager.find_best_node(feature=feature)
        if node is None and feature:
            raise NoNodeWithRequestFunctionalityAvailableException(
                _("No node with {feature_name_variable_do_not_translate} functionality available!").format(
                    feature_name_variable_do_not_translate=feature
                ),
                feature=feature,
            )
        try:
            response = await node.post_decodetracks(tracks, raise_on_failure=raise_on_failure)
            if isinstance(response, HTTPException):
                raise TypeError
            return response
        except Exception:  # noqa
            response_tracks = []
            for track in tracks:
                with contextlib.suppress(Exception):
                    response_tracks.append(decode_track(track))
            return response_tracks

    @staticmethod
    async def routeplanner_status(node: Node) -> RoutePlannerStatus:
        """|coro|
        Gets the route-planner status of the target node.

        Parameters
        ----------
        node: :class:`Node`
            The node to use for the query.

        Returns
        -------
        RoutePlannerStatusResponseObject
            An object representing the route-planner information.
        """
        return await node.fetch_routeplanner_status()

    @staticmethod
    async def routeplanner_free_address(node: Node, address: str) -> None:
        """|coro|
        Gets the route-planner status of the target node.

        Parameters
        ----------
        node: :class:`Node`
            The node to use for the query.
        address: :class:`str`
            The address to free.
        """
        return await node.post_routeplanner_free_address(address)

    @staticmethod
    async def routeplanner_free_all_failing(node: Node) -> None:
        """|coro|
        Gets the route-planner status of the target node.

        Parameters
        ----------
        node: :class:`Node`
            The node to use for the query.
        """
        return await node.post_routeplanner_free_all()

    def dispatch_event(self, event: PyLavEvent) -> None:
        """Dispatches the given event to all registered hooks."""
        asyncio.create_task(self._dispatch_event(event))

    async def _dispatch_event(self, event: PyLavEvent) -> None:
        """|coro|
        Dispatches the given event to all registered hooks.

        Parameters
        ----------
        event: :class:`Event`
            The event to dispatch to the hooks.
        """
        event_dispatcher = [self._dispatch_manager.dispatch]

        task_list = []
        for hook in itertools.chain(
            event_dispatcher,
        ):
            task = asyncio.create_task(hook(event))  # type: ignore
            task.set_name(f"Event hook {hook.__name__}")
            task.add_done_callback(self.__done_callback)
            task_list.append(task)
        await asyncio.gather(*task_list)

    @staticmethod
    def __done_callback(task: asyncio.Task) -> None:
        if (exc := task.exception()) is not None:
            name = task.get_name()
            LOGGER.warning("Event hook %s encountered an exception!", name)
            LOGGER.debug("Event hook %s encountered an exception!", name, exc_info=exc)

    async def unregister(self, cog: discord.ext.commands.Cog):
        """|coro|
        Unregister the specified Cog and if no cogs are left closes the client.

        Parameters
        ----------
        cog: :class:`discord.ext.commands.Cog`
            The cog to unregister.
        """
        if self._shutting_down:
            return
        async with self._asyncio_lock:
            if not self._shutting_down:
                self.__cogs_registered.discard(cog.__cog_name__)
                LOGGER.debug("%s has been unregistered", cog.__cog_name__)
                if not self.__cogs_registered:
                    self.bot.remove_listener(self.on_pylav_red_api_tokens_update, name="on_red_api_tokens_update")
                    self.bot.remove_listener(self.on_pylav_shard_resumed, name="on_shard_resumed")
                    self.bot.remove_listener(self.on_pylav_shard_ready, name="on_shard_ready")
                    self.bot.remove_listener(self.on_pylav_ready, name="on_ready")
                    self.bot.remove_listener(self.on_pylav_resumed, name="on_resumed")
                    self._shutting_down = True

                    self.ready.clear()
                    try:
                        Client._instances.clear()
                        SingletonCallable.reset()
                        self._initiated = False
                        await self.__local_tracks_cache.shutdown()
                        await self.player_manager.save_all_players()
                        await self.player_manager.shutdown()
                        await self._node_manager.close()
                        await self._local_node_manager.shutdown()
                        await self._session.close()
                        await self._cached_session.close()
                        await self._flowery_api.shutdown()

                        if self._scheduler:
                            with contextlib.suppress(Exception):
                                self._scheduler.shutdown(wait=True)
                    except Exception as e:
                        LOGGER.critical("Failed to shutdown the client", exc_info=e)
                    if self.__old_process_command_method is not None:
                        self.bot.process_commands = self.__old_process_command_method
                    if self.__old_get_context is not None:
                        self.bot.get_context = self.__old_get_context
                    del self.bot._pylav_client  # noqa
                    await DATABASE_ENGINE.close_connection_pool()
                    LOGGER.info("All cogs have been unregistered, PyLav client has been shutdown")
                    # self.__reload_pylav()

    @staticmethod
    def __reload_pylav():
        import importlib

        name = __name__.split(".")[0]
        temp = sorted(((k, v) for k, v in sys.modules.copy().items() if k.startswith(name)), reverse=True)
        for n, m in temp:
            if n.startswith(name):
                importlib.reload(m)

    def get_player(self, guild: discord.Guild | int | None) -> Player | None:
        """Gets the player for the target guild.

        Parameters
        ----------
        guild: :class:`discord.Guild`
            The guild to get the player for.

        Returns
        -------
        :class:`Player`
            The player for the target guild.
        """
        if not guild:
            return None
        if not isinstance(guild, int):
            guild = guild.id
        return self.player_manager.get(guild)

    async def connect_player(
        self,
        requester: discord.Member,
        channel: discord.channel.VocalGuildChannel,
        node: Node = None,
        self_deaf: bool | None = None,
    ) -> Player:
        """|coro|
        Connects the player for the target guild.

        Parameters
        ----------
        channel: :class:`discord.channel.VocalGuildChannel`
            The channel to connect to.
        node: :class:`Node`
            The node to use for the connection.
        self_deaf: :class:`bool`
            Whether the bot should be deafened.
        requester: :class:`discord.Member`
            The member requesting the connection.
        Returns
        -------
        :class:`Player`
            The player for the target guild.
        """
        return await self.player_manager.create(channel, channel.rtc_region, node, self_deaf, requester)

    async def construct_embed(
        self,
        *,
        embed: discord.Embed = None,
        colour: discord.Colour | int | None = None,
        color: discord.Colour | int | None = None,
        title: str = None,
        embed_type: EmbedType = "rich",
        url: str = None,
        description: str = None,
        timestamp: datetime.datetime = None,
        author_name: str = None,
        author_url: str = None,
        thumbnail: str = None,
        footer: str = None,
        footer_url: str = None,
        messageable: Messageable | DISCORD_INTERACTION_TYPE = None,
    ) -> discord.Embed:
        """|coro|
        Constructs an embed.
        """
        if messageable and not colour and not color and hasattr(self._bot, "get_embed_color"):
            colour = await self._bot.get_embed_color(messageable)
        elif colour or color:
            colour = colour or color
        if timestamp and isinstance(timestamp, datetime.datetime):
            timestamp = timestamp
        else:
            timestamp = get_now_utc()
        contents = dict(
            title=title,
            type=embed_type,
            url=url,
            description=description,
            timestamp=timestamp.isoformat(),
        )
        embed = embed.to_dict() if embed is not None else {}
        contents |= embed
        new_embed = discord.Embed.from_dict(contents)
        new_embed.color = colour

        if footer:
            new_embed.set_footer(text=footer, icon_url=footer_url)
        if thumbnail:
            new_embed.set_thumbnail(url=thumbnail)
        if author_url and author_name:
            new_embed.set_author(name=author_name, icon_url=author_url)
        return new_embed

    async def get_context(
        self, what: discord.Message | DISCORD_CONTEXT_TYPE | DISCORD_INTERACTION_TYPE
    ) -> PyLavContext:
        """|coro|
        Gets the context for the target message or interaction.
        """
        if isinstance(what, PyLavContext):
            return what
        elif isinstance(what, Context):
            ctx_ = what.interaction or what.message
            ctx: PyLavContext = await self._bot.get_context(ctx_, cls=PyLavContext)  # type: ignore

        else:
            ctx: PyLavContext = await self._bot.get_context(what, cls=PyLavContext)  # type: ignore
        return ctx

    async def update_localtracks_folder(self, folder: str | None) -> aiopath.AsyncPath:
        """|coro|
        Updates the localtracks folder.
        """
        if overrides.LOCAL_TRACKS_FOLDER:
            localtrack_folder = aiopath.AsyncPath(overrides.LOCAL_TRACKS_FOLDER)
        elif not folder:
            localtrack_folder = (
                aiopath.AsyncPath(LOCAL_TRACKS_FOLDER) if LOCAL_TRACKS_FOLDER else self._config_folder / "music"
            )
        else:
            localtrack_folder = aiopath.AsyncPath(folder)
        if not await localtrack_folder.exists():
            localtrack_folder = self._config_folder / "music"
        from pylav.players.query.local_files import LocalFile

        await self.lib_db_manager.get_config().update_localtrack_folder(await localtrack_folder.absolute())
        await LocalFile.add_root_folder(path=localtrack_folder, create=True)
        return localtrack_folder

    def get_all_players(self) -> Iterator[Player]:
        """Gets all players."""
        return iter(self.player_manager)

    def get_managed_node(self) -> Node | None:
        """Gets a managed node."""
        available_nodes = list(filter(operator.attrgetter("available"), self.node_manager.managed_nodes))

        return random.choice(available_nodes) if available_nodes else None

    def get_my_node(self) -> Node | None:
        """Gets the local node that is managed by PyLav."""
        return next(
            filter(lambda n: n.identifier == self.bot.user.id, self.node_manager.managed_nodes),
            None,
        )

    async def _get_tracks(
        self,
        query: Query,
        first: bool = False,
        bypass_cache: bool = False,
        player: Player | None = None,
    ) -> rest_api.LoadTrackResponses:
        """|coro|
        Gets all tracks associated with the given query.

        Parameters
        ----------
        query: :class:`Query`
            The query to perform a search for
        first: Optional[:class:`bool`]
            Whether to only return the first track. Defaults to `False`.
        bypass_cache: Optional[:class:`bool`]
            Whether to bypass the cache. Defaults to `False`.

        Returns
        -------
        :class:`LavalinkLoadTrackObjects`
            A LavalinkLoadTrackObjects representing Lavalink response.
        """
        if not self.node_manager.available_nodes:
            raise NoNodeAvailableException("There are no available nodes!")

        node = await self.node_manager.find_best_node(
            feature=query.requires_capability,
            region=player.region if player else None,
            coordinates=player.coordinates if player else None,
        )
        if node is None:
            raise NoNodeWithRequestFunctionalityAvailableException(
                _("No node with {feature_name_variable_do_not_translate} functionality available!").format(
                    feature_name_variable_do_not_translate=query.requires_capability
                ),
                query.requires_capability,
            )
        return await node.get_track(query, first=first, bypass_cache=bypass_cache)

    async def get_all_tracks_for_queries(
        self,
        *queries: Query,
        requester: discord.Member,
        player: Player | None = None,
        bypass_cache: bool = False,
        enqueue: bool = True,
    ) -> tuple[list[Track], int, list[Query]]:  # sourcery no-metrics
        """High level interface to get and return all tracks for a list of queries.

        This will automatically handle playlists, albums, searches and local files.

        Parameters
        ----------
        queries : `Query`
            The list of queries to search for.
        bypass_cache : `bool`, optional
            Whether to bypass the cache and force a new search.
            Local files will always be bypassed.
        requester : `discord.Member`
            The user who requested the op.
        player : `Player`
            The player requesting the op.
        enqueue : `bool`, optional
            Whether to enqueue the tracks as needed
            while try are processed so users dont sit waiting for the bot to finish.

        Returns
        -------
        tracks : `List[Track]`
            The list of tracks found.
        total_tracks : `int`
            The total number of tracks found.
        queries : `List[Query]`
            The list of queries that were not found.

        """
        successful_tracks = []
        queries_failed = []
        track_count = 0
        for query in queries:
            try:
                track_count = await self._get_tracks_single_query(
                    bypass_cache,
                    enqueue,
                    player,
                    queries_failed,
                    query,
                    requester,
                    successful_tracks,
                    track_count,
                )
            except Exception:
                queries_failed.append(query)
        return successful_tracks, track_count, queries_failed

    async def _get_tracks_single_query(
        self, bypass_cache, enqueue, player, queries_failed, query, requester, successful_tracks, track_count
    ):
        async for sub_query in self._yield_recursive_queries(query):
            node = await self.node_manager.find_best_node(
                region=player.region if player else None,
                coordinates=player.coordinates if player else None,
                feature=sub_query.requires_capability,
            )
            if node is None:
                queries_failed.append(sub_query)
                continue
            await self._get_tracks_play_or_enqueue(enqueue, player, requester, successful_tracks)
            if sub_query.is_search or sub_query.is_single:
                track_count = await self._get_tracks_search_or_single(
                    bypass_cache,
                    node,
                    player,
                    queries_failed,
                    requester,
                    sub_query,
                    successful_tracks,
                    track_count,
                )
            elif (
                (sub_query.is_playlist or sub_query.is_album)
                and not sub_query.is_local
                and not sub_query.is_custom_playlist
            ):
                track_count = await self._get_tracks_playlist_or_album_no_local(
                    bypass_cache,
                    enqueue,
                    node,
                    player,
                    queries_failed,
                    requester,
                    sub_query,
                    successful_tracks,
                    track_count,
                )
            elif (sub_query.is_local or sub_query.is_custom_playlist) and sub_query.is_album:
                track_count = await self._get_tracks_local_album(
                    enqueue, node, player, queries_failed, requester, sub_query, successful_tracks, track_count
                )
            else:
                queries_failed.append(sub_query)
                LOGGER.warning("Unhandled query: %s, %s", sub_query.to_dict(), sub_query.query_identifier)
        return track_count

    @staticmethod
    async def _get_tracks_play_or_enqueue(enqueue, player, requester, successful_tracks):
        # Query tracks as the queue builds as this may be a slow operation
        if player is None:
            return
        if enqueue and successful_tracks and not player.is_playing and not player.paused:
            track = successful_tracks.pop()
            await player.play(track, await track.query(), requester)
        elif successful_tracks and player.is_playing and player.queue.empty():
            track = successful_tracks.pop()
            await player.add(requester.id, track, query=await track.query())

    async def _get_tracks_local_album(
        self,
        enqueue,
        node,
        player,
        queries_failed,
        requester,
        sub_query,
        successful_tracks,
        track_count,
    ):
        yielded = False
        async for local_track in sub_query.get_all_tracks_in_folder():
            yielded = True
            response = await self._get_tracks(player=player, query=local_track, first=True, bypass_cache=True)
            match response.loadType:
                case "track":
                    tracks = [response.data]
                case "search":
                    tracks = response.data
                case "playlist":
                    tracks = response.data.tracks
                case __:
                    queries_failed.append(local_track)
                    continue
            if __ := tracks[0].encoded:
                track_count += 1
                successful_tracks.append(
                    await Track.build_track(
                        data=tracks[0], node=node, query=None, requester=requester.id, player_instance=player
                    )
                )
                # Query tracks as the queue builds as this may be a slow operation
                if enqueue and successful_tracks and not player.is_playing:
                    track = successful_tracks.pop()
                    await player.play(track, await track.query(), requester)
        if not yielded:
            queries_failed.append(sub_query)
        return track_count

    async def _get_tracks_playlist_or_album_no_local(
        self,
        bypass_cache,
        enqueue,
        node,
        player,
        queries_failed,
        requester,
        sub_query,
        successful_tracks,
        track_count,
    ):
        response = await self._get_tracks(player=player, query=sub_query, bypass_cache=bypass_cache)
        match response.loadType:
            case "track":
                tracks = [response.data]
                enqueue = False
            case "search":
                tracks = response.data
            case "playlist":
                tracks = response.data.tracks
            case __:
                queries_failed.append(sub_query)
                return track_count
        if not tracks:
            queries_failed.append(sub_query)
        for track in tracks:
            if __ := track.encoded:
                track_count += 1
                successful_tracks.append(
                    await Track.build_track(
                        data=track, node=node, query=None, requester=requester.id, player_instance=player
                    )
                )
                # Query tracks as the queue builds as this may be a slow operation
                if enqueue and successful_tracks and not player.is_playing:
                    track = successful_tracks.pop()
                    await player.play(track, await track.query(), requester)
        return track_count

    async def _get_tracks_search_or_single(
        self, bypass_cache, node, player, queries_failed, requester, sub_query, successful_tracks, track_count
    ):
        response = await self._get_tracks(player=player, query=sub_query, first=True, bypass_cache=bypass_cache)
        match response.loadType:
            case "track":
                tracks = [response.data]
            case "search":
                tracks = response.data
            case "playlist":
                tracks = response.data.tracks
            case __:
                queries_failed.append(sub_query)
                return track_count
        if tracks:
            track_count += 1
            new_query = await Query.from_string(tracks[0].info.uri)
            new_query.merge(sub_query, start_time=True)
            successful_tracks.append(
                await Track.build_track(
                    data=tracks[0], node=node, query=sub_query, requester=requester.id, player_instance=player
                )
            )
        else:
            queries_failed.append(sub_query)
        return track_count

    @staticmethod
    async def _yield_recursive_queries(query: Query, recursion_depth: int = 0) -> AsyncIterator[Query]:
        """|coro|
        Gets all queries associated with the given query.
        Parameters
        ----------
        query: :class:`Query`
            The query to perform a search for
        """
        if query.invalid or recursion_depth > MAX_RECURSION_DEPTH:
            return
        recursion_depth += 1
        if query.is_m3u:
            # noinspection PyProtectedMember
            async for m3u in query._yield_m3u_tracks():
                with contextlib.suppress(Exception):
                    # noinspection PyProtectedMember
                    async for q in query._yield_tracks_recursively(m3u, recursion_depth):
                        yield q
        elif query.is_pylav:
            # noinspection PyProtectedMember
            async for pylav in query._yield_pylav_file_tracks():
                with contextlib.suppress(Exception):
                    # noinspection PyProtectedMember
                    async for q in query._yield_tracks_recursively(pylav, recursion_depth):
                        yield q
        elif query.is_pls:
            # noinspection PyProtectedMember
            async for pls in query._yield_pls_tracks():
                with contextlib.suppress(Exception):
                    # noinspection PyProtectedMember
                    async for q in query._yield_tracks_recursively(pls, recursion_depth):
                        yield q
        elif query.is_local and query.is_album:
            # noinspection PyProtectedMember
            async for local in query._yield_local_tracks():
                yield local
        else:
            yield query

    async def get_tracks(
        self,
        *queries: Query,
        bypass_cache: bool = False,
        fullsearch: bool = False,
        region: str | None = None,
        player: Player | None = None,
        sleep: bool = False,
    ) -> rest_api.LoadTrackResponses:  # sourcery skip: low-code-quality
        """This method can be rather slow as it recursively queries all queries and their associated entries.

        Thus, if you are processing user input you may be interested in using
        the :meth:`get_all_tracks_for_queries` where it can enqueue tracks as needed to the player.


        Parameters
        ----------
        queries : `Query`
            The list of queries to search for.
        bypass_cache : `bool`, optional
            Whether to bypass the cache and force a new search.
            Local files will always be bypassed.
        fullsearch : `bool`, optional
            if a Search query is passed wether to returrn a list of tracks instead of the first.
        region : `str`, optional
            The region to search in.
        player : `Player`, optional
            The player to use for enqueuing tracks.
        sleep : `bool`, optional
            Whether to sleep between each query to avoid ratelimits.
        """
        output_tracks = []
        playlist_name = ""
        plugin_info = {}

        if region is None and player is not None:
            region = player.region
        if region is None:
            region = "us_east"
        for query in queries:
            async for subquery in self._yield_recursive_queries(query):
                response = await self.search_query(
                    subquery, bypass_cache=bypass_cache, fullsearch=fullsearch, region=region, sleep=sleep
                )
                match response.loadType:
                    case "track":
                        tracks = [response.data]
                        playlist_name = ""
                    case "search":
                        tracks = response.data
                        playlist_name = ""
                    case "playlist":
                        tracks = response.data.tracks
                        plugin_info |= response.data.pluginInfo.to_dict()
                        playlist_name = response.data.info.name if response.data.info else ""
                    case __:
                        continue
                if subquery.is_playlist or subquery.is_album:
                    output_tracks.extend(tracks)
                elif fullsearch and subquery.is_search or subquery.is_single:
                    output_tracks.extend(tracks)
                else:
                    LOGGER.error("Unknown query type: %s", subquery)
        data = {
            "loadType": "playlist"
            if playlist_name and len(queries) == 1
            else "search"
            if len(output_tracks) > 1
            else "track"
            if output_tracks
            else "empty",
            "data": None,
        }
        match data["loadType"]:
            case "playlist":
                data["data"] = {
                    "info": {"name": playlist_name, "selectedTrack": 0},
                    "pluginInfo": plugin_info,
                    "tracks": [track.to_dict() for track in output_tracks],
                }
            case "search":
                data["data"] = [track.to_dict() for track in output_tracks]
            case "track":
                data["data"] = output_tracks[0].to_dict()
            case "empty":
                data["data"] = None
            case "error" | "apiError":
                data["data"] = {"cause": "No tracks returned", "severity": "common", "message": "No tracks found"}

        node = await self.node_manager.find_best_node()
        while not node:
            await asyncio.sleep(0.1)
            node = await self.node_manager.find_best_node()
        return node.parse_loadtrack_response(data)

    async def search_query(
        self,
        query: Query,
        bypass_cache: bool = False,
        fullsearch: bool = False,
        region: str | None = None,
        sleep: bool = False,
    ) -> rest_api.LoadTrackResponses | None:
        """
        Search for the specified query returns a LoadTrackResponse object


        Parameters
        ----------
        query : `Query`
            The list of queries to search for.
        bypass_cache : `bool`, optional
            Whether to bypass the cache and force a new search.
            Local files will always be bypassed.
        fullsearch : `bool`, optional
            if a Search query is passed wether to returrn a list of tracks instead of the first.
        region : `str`, optional
            The region to search in.
        sleep : `bool`, optional
            Whether to sleep for a short duration if a lavalink call is made.
        """
        node = await self.node_manager.find_best_node(region=region, feature=query.requires_capability)
        if node is None:
            return
        if query.is_playlist or query.is_album or (fullsearch and query.is_search):
            return await node.get_track(query, bypass_cache=bypass_cache, sleep=sleep)
        elif query.is_single:
            return await node.get_track(query, first=True, bypass_cache=bypass_cache, sleep=sleep)
        else:
            LOGGER.error("Unknown query type: %s", query)

    async def remove_node(self, node_id: int):
        """Removes a node from the node manager"""
        if node := self.node_manager.get_node_by_id(node_id):
            await self.node_manager.remove_node(node)

    async def is_dj(
        self,
        user: discord.Member,
        guild: discord.Guild,
        *,
        additional_role_ids: list = None,
        additional_user_ids: list = None,
    ) -> bool:
        """Checks if a user is a DJ in a guild."""
        if additional_user_ids and user.id in additional_user_ids:
            return True
        if additional_role_ids and any(r.id in additional_role_ids for r in user.roles):
            return True
        return await self.player_config_manager.is_dj(
            user=user, guild=guild, additional_role_ids=None, additional_user_ids=None
        )

    @staticmethod
    async def generate_mix_playlist(
        *,
        video_id: str | None = None,
        user_id: str | None = None,
        playlist_id: str | None = None,
        channel_id: str | None = None,
    ) -> str:
        """Generates an YouTube mixed playlist url from a single video, user, channel or playlist."""
        if not any([video_id, playlist_id, channel_id, user_id]):
            raise PyLavInvalidArgumentsException(
                _("A single video, user, channel or playlist identifier is necessary to generate a mixed playlist.")
            )

        if sum(1 for i in [video_id, playlist_id, channel_id, user_id] if i) > 1:
            raise PyLavInvalidArgumentsException(
                _(
                    "A single video, user, channel or playlist identifier is necessary to generate a mixed playlist. "
                    "However, you provided multiple"
                )
            )

        if video_id:
            return f"https://www.youtube.com/watch?list=RD{video_id}"
        if user_id:
            return f"https://www.youtube.com/watch?list=UU{user_id}"
        if playlist_id:
            return f"https://www.youtube.com/watch?list=RDAMPL{playlist_id}"
        if channel_id:
            return f"https://www.youtube.com/watch?list=RDCM{channel_id}"
