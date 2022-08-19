from __future__ import annotations

import datetime
import gzip
import io
import re
import sys
from collections.abc import Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import aiohttp
import asyncstdlib
import discord
import ujson
import yaml
from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

try:
    import brotli

    BROTLI_ENABLED = False
except ImportError:
    BROTLI_ENABLED = False

from pylav._config import CONFIG_DIR
from pylav._logging import getLogger
from pylav.constants import BUNDLED_PLAYLIST_IDS, SUPPORTED_SOURCES
from pylav.exceptions import InvalidPlaylist
from pylav.filters import Equalizer
from pylav.sql import tables
from pylav.types import BotT
from pylav.utils import PyLavContext, TimedFeature

BRACKETS: re.Pattern = re.compile(r"[\[\]]")

LOGGER = getLogger("PyLav.DBModels")


@dataclass(eq=True)
class PlaylistModel:
    id: int
    scope: int
    author: int
    name: str
    tracks: list[str] = field(default_factory=list)
    url: str | None = None

    def __post_init__(self):
        if isinstance(self.tracks, str):
            self.tracks = ujson.loads(self.tracks)

    async def save(self) -> PlaylistModel:
        """Save the playlist to the database.
        Returns
        -------
        PlaylistModel
            The saved playlist.
        """
        values = {
            tables.PlaylistRow.scope: self.scope,
            tables.PlaylistRow.author: self.author,
            tables.PlaylistRow.name: self.name,
            tables.PlaylistRow.url: self.url,
            tables.PlaylistRow.tracks: self.tracks,
        }
        playlist = (
            await tables.PlaylistRow.objects()
            .output(load_json=True)
            .get_or_create(tables.PlaylistRow.id == self.id, defaults=values)
        )
        if not playlist._was_created:
            await tables.PlaylistRow.update(values).where(tables.PlaylistRow.id == self.id)
        return PlaylistModel(**playlist.to_dict())

    @classmethod
    async def get(cls, id: int) -> PlaylistModel | None:
        """Get a playlist from the database.

        Parameters
        ----------
        id : int
            The id of the playlist.

        Returns
        -------
        PlaylistModel | None
            The playlist if it exists, otherwise None.
        """
        playlist = await tables.PlaylistRow.select().where(tables.PlaylistRow.id == id)
        if playlist:
            return PlaylistModel(**playlist.to_dict())
        return None

    async def delete(self) -> None:
        """Delete the playlist from the database."""
        await tables.PlaylistRow.delete().where(tables.PlaylistRow.id == self.id)

    async def can_manage(self, bot: BotT, requester: discord.abc.User, guild: discord.Guild = None) -> bool:
        """Check if the requester can manage the playlist.

        Parameters
        ----------
        bot : BotT
            The bot instance.
        requester : discord.abc.User
            The requester.
        guild : discord.Guild
            The guild.

        Returns
        -------
        bool
            Whether the requester can manage the playlist.
        """
        if self.scope in BUNDLED_PLAYLIST_IDS:
            return False
        if requester.id in ((ids := getattr(bot, "owner_ids")) or ()) or requester.id == bot.owner_id:  # noqa
            return True
        elif self.scope == bot.user.id:
            return False
        return self.author == requester.id

    async def get_scope_name(self, bot: BotT, mention: bool = True, guild: discord.Guild = None) -> str:
        """Get the name of the scope of the playlist.

        Parameters
        ----------
        bot : BotT
            The bot instance.
        mention : bool
            Whether to add a mention if it is mentionable.
        guild : discord.Guild
            The guild to get the scope name for.

        Returns
        -------
        str
            The name of the scope of the playlist.
        """
        if bot.user.id == self.scope:
            return f"(Global) {bot.user.mention}" if mention else f"(Global) {bot.user}"
        elif guild_ := bot.get_guild(self.scope):
            if guild_:
                guild = guild_
            return f"(Server) {guild.name}"
        elif guild and (channel := guild.get_channel_or_thread(self.scope)):
            return f"(Channel) {channel.mention}" if mention else f"(Channel) {channel.name}"

        elif (
            (guild := guild_ or guild)
            and (guild and (author := guild.get_member(self.scope)))
            or (author := bot.get_user(self.author))
        ):
            return f"(User) {author.mention}" if mention else f"(User) {author}"
        else:
            return f"(Invalid) {self.scope}"

    async def get_author_name(self, bot: BotT, mention: bool = True) -> str | None:
        """Get the name of the author of the playlist.

        Parameters
        ----------
        bot : BotT
            The bot instance.
        mention : bool
            Whether to add a mention if it is mentionable.

        Returns
        -------
        str | None
            The name of the author of the playlist.
        """
        if user := bot.get_user(self.author):
            return f"{user.mention}" if mention else f"{user}"
        return f"{self.author}"

    async def get_name_formatted(self, with_url: bool = True) -> str:
        """Get the name of the playlist formatted.

        Parameters
        ----------
        with_url : bool
            Whether to include the url in the name.

        Returns
        -------
        str
            The formatted name.
        """
        name = BRACKETS.sub("", self.name).strip()
        if with_url and self.url and self.url.startswith("http"):
            return f"**[{discord.utils.escape_markdown(name)}]({self.url})**"
        else:
            return f"**{discord.utils.escape_markdown(name)}**"

    @asynccontextmanager
    async def to_yaml(self, guild: discord.Guild) -> Iterator[tuple[io.BytesIO, str | None]]:
        """Serialize the playlist to a YAML file.

        yields a tuple of (io.BytesIO, bool) where the bool is whether the playlist file was compressed using Gzip

        Parameters
        ----------
        guild : discord.Guild
            The guild where the yaml will be sent to.

        Yields
        ------
        tuple[io.BytesIO, str | None]
            The YAML file and the compression type.
        """
        data = {
            "name": self.name,
            "author": self.author,
            "url": self.url,
            "tracks": self.tracks,
        }
        compression = None
        with io.BytesIO() as bio:
            yaml.safe_dump(data, bio, default_flow_style=False, sort_keys=False, encoding="utf-8")
            bio.seek(0)
            LOGGER.debug(f"SIZE UNCOMPRESSED playlist ({self.name}): {sys.getsizeof(bio)}")
            if sys.getsizeof(bio) > guild.filesize_limit:
                with io.BytesIO() as bio:
                    if BROTLI_ENABLED:
                        compression = "brotli"
                        bio.write(brotli.compress(yaml.dump(data, encoding="utf-8")))
                    else:
                        compression = "gzip"
                        with gzip.GzipFile(fileobj=bio, mode="wb", compresslevel=9) as gfile:
                            yaml.safe_dump(data, gfile, default_flow_style=False, sort_keys=False, encoding="utf-8")
                    bio.seek(0)
                    LOGGER.debug(f"SIZE COMPRESSED playlist [{compression}] ({self.name}): {sys.getsizeof(bio)}")
                    yield bio, compression
                    return
            yield bio, compression

    @classmethod
    async def from_yaml(cls, context: PyLavContext, scope: int, url: str) -> PlaylistModel:
        """Deserialize a playlist from a YAML file.

        Parameters
        ----------
        context : PyLavContext
            The context.
        scope : int
            The scope of the playlist.
        url : str
            The url of the playlist.

        Returns
        -------
        PlaylistModel
            The playlist.
        """
        try:
            async with aiohttp.ClientSession(auto_decompress=False) as session:
                async with session.get(url) as response:
                    data = await response.read()
                    data = gzip.decompress(data)
                    data = yaml.safe_load(data)
        except Exception as e:
            raise InvalidPlaylist(f"Invalid playlist file - {e}") from e
        return cls(
            id=context.message.id,
            scope=scope,
            author=data["author"],
            name=data["name"],
            url=data["url"],
            tracks=data["tracks"],
        )


@dataclass(eq=True)
class LibConfigModel:
    bot: int
    id: int = 1
    config_folder: str | None = None
    localtrack_folder: str | None = None
    java_path: str | None = None
    enable_managed_node: bool | None = None
    use_bundled_external: bool = True
    auto_update_managed_nodes: bool | None = None
    download_id: int = 0
    extras: dict = field(default_factory=dict)
    next_execution_update_bundled_playlists: datetime.datetime | None = None
    next_execution_update_bundled_external_playlists: datetime.datetime | None = None
    next_execution_update_external_playlists: datetime.datetime | None = None
    update_bot_activity: bool = False

    def __post_init__(self):
        if isinstance(self.extras, str):
            self.extras = ujson.loads(self.extras)

    async def get_config_folder(self) -> str:
        """Get the config folder.

        Returns
        -------
        str
            The config folder.
        """
        response = (
            await tables.LibConfigRow.select(tables.LibConfigRow.config_folder)
            .where((tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot))
            .first()
        )
        return response["config_folder"]

    async def get_java_path(self) -> str:
        """Get the java path.

        Returns
        -------
        str
            The java path.
        """
        response = (
            await tables.LibConfigRow.select(tables.LibConfigRow.java_path)
            .where((tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot))
            .first()
        )
        return response["java_path"]

    async def get_enable_managed_node(self) -> bool:
        """Get whether the managed node is enabled.

        Returns
        -------
        bool
            Whether the managed node is enabled.
        """
        response = (
            await tables.LibConfigRow.select(tables.LibConfigRow.enable_managed_node)
            .where((tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot))
            .first()
        )
        return response["enable_managed_node"]

    async def get_auto_update_managed_nodes(self) -> bool:
        """Get whether the managed node should be auto updated.

        Returns
        -------
        bool
            Whether the managed node should be auto updated.
        """
        response = (
            await tables.LibConfigRow.select(tables.LibConfigRow.auto_update_managed_nodes)
            .where((tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot))
            .first()
        )
        return response["auto_update_managed_nodes"]

    async def get_localtrack_folder(self) -> str:
        """Get the localtrack folder.

        Returns
        -------
        str
            The localtrack folder.
        """
        response = (
            await tables.LibConfigRow.select(tables.LibConfigRow.localtrack_folder)
            .where((tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot))
            .first()
        )
        return response["localtrack_folder"]

    async def get_download_id(self) -> int:
        """Get the download id for the managed node.

        Returns
        -------
        int
            The download id for the managed node.
        """
        response = (
            await tables.LibConfigRow.select(tables.LibConfigRow.download_id)
            .where((tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot))
            .first()
        )
        return response["download_id"]

    async def get_next_execution_update_bundled_playlists(self) -> datetime.datetime:
        """Get the next execution time for the update of bundled playlists.

        Returns
        -------
        datetime.datetime
            The next execution time for the update of bundled playlists.
        """
        response = (
            await tables.LibConfigRow.select(tables.LibConfigRow.next_execution_update_bundled_playlists)
            .where((tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot))
            .first()
        )
        return response["next_execution_update_bundled_playlists"]

    async def get_next_execution_update_bundled_external_playlists(self) -> datetime.datetime:
        """Get the next execution time for the update of bundled external playlists.

        Returns
        -------
        datetime.datetime
            The next execution time for the update of bundled external playlists.
        """
        response = (
            await tables.LibConfigRow.select(tables.LibConfigRow.next_execution_update_bundled_external_playlists)
            .where((tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot))
            .first()
        )
        return response["next_execution_update_bundled_external_playlists"]

    async def get_next_execution_update_external_playlists(self) -> datetime.datetime:
        """Get the next execution time for the update of external playlists.

        Returns
        -------
        datetime.datetime
            The next execution time for the update of external playlists.
        """
        response = (
            await tables.LibConfigRow.select(tables.LibConfigRow.next_execution_update_external_playlists)
            .where((tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot))
            .first()
        )
        return response["next_execution_update_external_playlists"]

    async def get_update_bot_activity(self) -> bool:
        """Get whether the bot activity should be updated.

        Returns
        -------
        bool
            Whether the bot activity should be updated.
        """
        response = (
            await tables.LibConfigRow.select(tables.LibConfigRow.update_bot_activity)
            .where((tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot))
            .first()
        )
        return response["update_bot_activity"]

    async def set_config_folder(self, value: str) -> None:
        """Set the config folder.

        Parameters
        ----------
        value : str
            The new config folder.
        """
        self.config_folder = value
        await tables.LibConfigRow.update({tables.LibConfigRow.config_folder: value}).where(
            (tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot)
        )

    async def set_java_path(self, value: str) -> None:
        """Set the java path.

        Parameters
        ----------
        value : str
            The new java path.
        """
        self.java_path = value
        await tables.LibConfigRow.update({tables.LibConfigRow.java_path: value}).where(
            (tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot)
        )

    async def set_enable_managed_node(self, value: bool) -> None:
        """Set whether the managed node is enabled.


        Parameters
        ----------
        value : bool
            Whether the managed node is enabled.
        """
        self.enable_managed_node = value
        await tables.LibConfigRow.update({tables.LibConfigRow.enable_managed_node: value}).where(
            (tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot)
        )

    async def set_auto_update_managed_nodes(self, value: bool) -> None:
        """Set whether the managed node should be auto updated.

        Parameters
        ----------
        value : bool
            Whether the managed node should be auto updated.
        """
        self.auto_update_managed_nodes = value
        await tables.LibConfigRow.update({tables.LibConfigRow.auto_update_managed_nodes: value}).where(
            (tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot)
        )

    async def set_localtrack_folder(self, value: str) -> None:
        """Set the localtrack folder.

        Parameters
        ----------
        value : str
            The new localtrack folder.
        """
        self.localtrack_folder = value
        await tables.LibConfigRow.update({tables.LibConfigRow.localtrack_folder: value}).where(
            (tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot)
        )

    async def set_download_id(self, value: int) -> None:
        """Set the download id for the managed node.

        Parameters
        ----------
        value : int
            The new download id for the managed node.
        """
        self.download_id = value
        await tables.LibConfigRow.update({tables.LibConfigRow.download_id: value}).where(
            (tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot)
        )

    async def set_managed_external_node(self, value: bool) -> None:
        """Set whether the managed external node is enabled.

        Parameters
        ----------
        value : bool
            Whether the managed external node is enabled.
        """
        self.use_bundled_external = value
        await self.save()

    async def set_update_bot_activity(self, value: bool) -> None:
        """Set whether the bot activity should be updated.

        Parameters
        ----------
        value : bool
            Whether the bot activity should be updated.
        """
        self.update_bot_activity = value
        await self.save()

    async def save(self) -> LibConfigModel:
        """Save the config to the database.

        Returns
        -------
        LibConfigModel
            The updated config.
        """
        data = {
            "config_folder": self.config_folder,
            "java_path": self.java_path,
            "enable_managed_node": self.enable_managed_node,
            "auto_update_managed_nodes": self.auto_update_managed_nodes,
            "localtrack_folder": self.localtrack_folder,
            "use_bundled_external": self.use_bundled_external,
            "extras": self.extras,
            "download_id": self.download_id,
            "next_execution_update_bundled_playlists": self.next_execution_update_bundled_playlists,
            "next_execution_update_bundled_external_playlists": self.next_execution_update_bundled_external_playlists,
            "next_execution_update_external_playlists": self.next_execution_update_external_playlists,
            "update_bot_activity": self.update_bot_activity,
        }
        await tables.LibConfigRow.update(**data).where(
            (tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot)
        )
        return self

    async def delete(self) -> None:
        """Delete the config from the database."""
        await tables.LibConfigRow.delete().where(
            (tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot)
        )

    async def get_all(self) -> LibConfigModel:
        """Update all attributed for the config from the database.

        Returns
        -------
        LibConfigModel
            The updated config.
        """
        response = (
            await tables.LibConfigRow.select()
            .where((tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot))
            .first()
        )
        self.config_folder = response["config_folder"]
        self.java_path = response["java_path"]
        self.enable_managed_node = response["enable_managed_node"]
        self.auto_update_managed_nodes = response["auto_update_managed_nodes"]
        self.localtrack_folder = response["localtrack_folder"]
        self.use_bundled_external = response["use_bundled_external"]
        self.download_id = response["download_id"]
        self.next_execution_update_bundled_playlists = response["next_execution_update_bundled_playlists"]
        self.next_execution_update_bundled_external_playlists = response[
            "next_execution_update_bundled_external_playlists"
        ]
        self.next_execution_update_external_playlists = response["next_execution_update_external_playlists"]
        self.extras = ujson.loads(response["extras"]) if isinstance(response["extras"], str) else response["extras"]
        self.update_bot_activity = response["update_bot_activity"]
        return self

    @classmethod
    async def get_or_create(
        cls,
        id: int,
        bot: int,
        config_folder=str(CONFIG_DIR),
        localtrack_folder=str(CONFIG_DIR / "music"),
        java_path="java",
        enable_managed_node: bool = True,
        auto_update_managed_nodes: bool = True,
        use_bundled_external: bool = True,
    ) -> LibConfigModel:

        """Get or create a config for the bot.

        Parameters
        ----------
        id : int
            The config id.
        bot : int
            The id of the bot.
        config_folder : str
            The config folder.
        localtrack_folder : str
            The localtrack folder.
        java_path : str
            The java path.
        enable_managed_node : bool
            Whether the managed node is enabled.
        auto_update_managed_nodes : bool
            Whether the managed node should be auto updated.
        use_bundled_external : bool
            Whether the bundled external node is used.

        Returns
        -------
        LibConfigModel
            The config.
        """
        r = (
            await tables.LibConfigRow.objects()
            .output(load_json=True)
            .get_or_create(
                (tables.LibConfigRow.id == id) & (tables.LibConfigRow.bot == bot),
                defaults=dict(
                    config_folder=config_folder,
                    java_path=java_path,
                    localtrack_folder=localtrack_folder,
                    enable_managed_node=enable_managed_node,
                    auto_update_managed_nodes=auto_update_managed_nodes,
                    use_bundled_external=use_bundled_external,
                    download_id=0,
                    extras={},
                    next_execution_update_bundled_playlists=None,
                    next_execution_update_bundled_external_playlists=None,
                    next_execution_update_external_playlists=None,
                    update_bot_activity=False,
                ),
            )
        )
        return cls(**r.to_dict())


@dataclass(eq=True)
class NodeModel:
    id: int
    name: str
    ssl: bool
    resume_key: str | None
    resume_timeout: int
    reconnect_attempts: int
    search_only: bool
    managed: bool
    extras: dict
    yaml: dict
    disabled_sources: field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.extras, str):
            self.extras = ujson.loads(self.extras)
            if "max_ram" not in self.extras:
                self.extras["max_ram"] = "2048M"
        if isinstance(self.yaml, str):
            self.yaml = ujson.loads(self.yaml)
        if isinstance(self.disabled_sources, str):
            self.disabled_sources = ujson.loads(self.disabled_sources)

    @classmethod
    async def from_id(cls, id: int) -> NodeModel:
        """Get a node from the database.

        Parameters
        ----------
        id : int
            The id of the node.

        Returns
        -------
        NodeModel
            The node.
        """
        response = await tables.NodeRow.select().where(tables.NodeRow.id == id).first()
        return cls(**response)

    def to_dict(self) -> dict:
        """Convert the node to a dict.

        Returns
        -------
        dict
            The node as a dict.
        """
        return {
            "id": self.id,
            "name": self.name,
            "ssl": self.ssl,
            "resume_key": self.resume_key,
            "resume_timeout": self.resume_timeout,
            "reconnect_attempts": self.reconnect_attempts,
            "search_only": self.search_only,
            "managed": self.managed,
            "extras": self.extras,
            "yaml": self.yaml,
            "disabled_sources": self.disabled_sources,
        }

    def get_connection_args(self) -> dict:
        """Get the connection args for the node.

        Returns
        -------
        dict
            The connection args.

        Raises
        ------
        ValueError
            If the node is misconfigured in the database.
        """
        if self.yaml is None:
            raise ValueError("Node Connection config set")
        return {
            "unique_identifier": self.id,
            "host": self.yaml["server"]["address"],
            "port": self.yaml["server"]["port"],
            "password": self.yaml["lavalink"]["server"]["password"],
            "name": self.name,
            "ssl": self.ssl,
            "reconnect_attempts": self.reconnect_attempts,
            "search_only": self.search_only,
            "resume_timeout": self.resume_timeout,
            "resume_key": self.resume_key,
            "disabled_sources": self.disabled_sources,
            "managed": self.managed,
        }

    async def add_bulk_source_to_exclusion_list(self, *source: str):
        """Add sources to the exclusion list.

        Parameters
        ----------
        source : str
            The sources to add.
        """
        source = set(map(str.strip, map(str.lower, source)))
        if unsupported := source - SUPPORTED_SOURCES:
            raise ValueError(f"Unsupported sources: {unsupported}\nSupported sources: {SUPPORTED_SOURCES}")
        intersection = source & SUPPORTED_SOURCES
        intersection |= set(self.disabled_sources)
        self.disabled_sources = list(intersection)
        await self.save()

    async def add_source_to_exclusion_list(self, source: str):
        """Add a source to the exclusion list.

        Parameters
        ----------
        source : str
            The source to add.
        """
        source = source.lower().strip()
        if source in SUPPORTED_SOURCES and source not in self.disabled_sources:
            self.disabled_sources.append(source)
            await self.save()
        raise ValueError(f"Source {source} is not supported")

    async def save(self) -> None:
        """Save the node to the database."""
        await self.upsert()

    async def delete(self) -> None:
        """Delete the node from the database."""
        await tables.NodeRow.delete().where(tables.NodeRow.id == self.id)

    async def upsert(self) -> None:
        """Upsert the node in the database."""
        values = {
            tables.NodeRow.name: self.name,
            tables.NodeRow.ssl: self.ssl,
            tables.NodeRow.resume_key: self.resume_key,
            tables.NodeRow.reconnect_attempts: self.reconnect_attempts,
            tables.NodeRow.resume_timeout: self.resume_timeout,
            tables.NodeRow.search_only: self.search_only,
            tables.NodeRow.managed: self.managed,
            tables.NodeRow.extras: self.extras,
            tables.NodeRow.yaml: self.yaml,
            tables.NodeRow.disabled_sources: self.disabled_sources,
        }
        node = (
            await tables.NodeRow.objects()
            .output(load_json=True)
            .get_or_create(tables.NodeRow.id == self.id, defaults=values)
        )
        if not node._was_created:
            await tables.NodeRow.update(values).where(tables.NodeRow.id == self.id)

    async def update_or_create(self) -> None:
        """Update or create the node in the database."""
        values = {
            tables.NodeRow.name: self.name,
            tables.NodeRow.ssl: self.ssl,
            tables.NodeRow.resume_key: self.resume_key,
            tables.NodeRow.reconnect_attempts: self.reconnect_attempts,
            tables.NodeRow.resume_timeout: self.resume_timeout,
            tables.NodeRow.search_only: self.search_only,
            tables.NodeRow.managed: self.managed,
            tables.NodeRow.extras: self.extras,
            tables.NodeRow.yaml: self.yaml,
            tables.NodeRow.disabled_sources: self.disabled_sources,
        }
        output = (
            await tables.NodeRow.objects()
            .output(load_json=True)
            .get_or_create(tables.NodeRow.id == self.id, defaults=values)
        )
        if not output._was_created:
            self.name = output.name
            self.ssl = output.ssl
            self.reconnect_attempts = output.reconnect_attempts
            self.search_only = output.search_only
            self.extras = output.extras
            self.managed = output.managed
            self.yaml = output.yaml
            self.resume_key = output.resume_key
            self.resume_timeout = output.resume_timeout
            self.disabled_sources = output.disabled_sources


@dataclass(eq=True)
class QueryModel:
    identifier: str
    name: str | None = None
    last_updated: datetime.datetime = None
    tracks: list[str] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.tracks, str):
            self.tracks = ujson.loads(self.tracks)

    @classmethod
    async def get(cls, identifier: str) -> QueryModel | None:
        """Get a query from the database.

        Parameters
        ----------
        identifier : str
            The identifier of the query.

        Returns
        -------
        QueryModel | None
            The query if found, otherwise None.
        """
        query = await tables.QueryRow.select().where(
            (tables.QueryRow.identifier == identifier)
            & (
                tables.QueryRow.last_updated
                > datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30)
            )
        )
        data = query.to_dict()
        if query:
            return QueryModel(**data)
        return None

    async def delete(self):
        """Delete the query from the database."""
        await tables.QueryRow.delete().where(tables.QueryRow.identifier == self.identifier)

    async def upsert(self):
        """Upsert the query in the database."""
        if self.last_updated is None:
            self.last_updated = datetime.datetime.now(tz=datetime.timezone.utc)
        values = {
            tables.QueryRow.tracks: self.tracks,
            tables.QueryRow.last_updated: self.last_updated,
            tables.QueryRow.name: self.name,
        }
        query = (
            await tables.QueryRow.objects()
            .output(load_json=True)
            .get_or_create(
                (tables.QueryRow.identifier == self.identifier)
                & (
                    tables.QueryRow.last_updated
                    > datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30)
                ),
                defaults=values,
            )
        )
        if not query._was_created:
            await tables.QueryRow.update(values).where(tables.QueryRow.identifier == self.identifier)

    async def save(self):
        """Save the query to the database."""
        await self.upsert()


@dataclass(eq=True)
class BotVersion:
    bot: int
    version: str | LegacyVersion | Version

    def __post_init__(self):
        if isinstance(self.version, str):
            self.version = parse_version(self.version)  # type: ignore

    async def get_or_create(self) -> BotVersion:
        """Get or create the bot version in the database.

        Returns
        -------
        BotVersion
            The bot version.
        """
        values = {
            tables.BotVersionRow.version: f"{self.version}",
        }
        output = (
            await tables.BotVersionRow.objects()
            .output(load_json=True)
            .get_or_create(tables.BotVersionRow.bot == self.bot, defaults=values)
        )
        if not output._was_created:
            self.version = parse_version(output.version)
        return self

    async def upsert(self) -> None:
        """Upsert the bot version in the database."""
        values = {
            tables.BotVersionRow.version: f"{self.version}",
        }
        node = (
            await tables.BotVersionRow.objects()
            .output(load_json=True)
            .get_or_create(tables.BotVersionRow.bot == self.bot, defaults=values)
        )
        if not node._was_created:
            await tables.BotVersionRow.update(values).where(tables.BotVersionRow.bot == self.bot)

    async def save(self) -> None:
        """Save the bot version to the database."""
        await self.upsert()


@dataclass(eq=True)
class PlayerStateModel:
    id: int
    bot: int
    channel_id: int
    volume: int
    position: float
    auto_play_playlist_id: int | None
    text_channel_id: int | None
    notify_channel_id: int | None
    forced_channel_id: int | None

    paused: bool
    repeat_current: bool
    repeat_queue: bool
    shuffle: bool
    auto_shuffle: bool
    auto_play: bool
    playing: bool
    effect_enabled: bool
    self_deaf: bool

    current: dict | None
    queue: list
    history: list
    effects: dict
    extras: dict

    def __post_init__(self):
        if isinstance(self.current, str):
            self.current = ujson.loads(self.current)
        if isinstance(self.queue, str):
            self.queue = ujson.loads(self.queue)
        if isinstance(self.history, str):
            self.history = ujson.loads(self.history)
        if isinstance(self.effects, str):
            self.effects = ujson.loads(self.effects)
        if isinstance(self.extras, str):
            self.extras = ujson.loads(self.extras)

    async def delete(self) -> None:
        """Delete the player state from the database."""
        await tables.PlayerStateRow.delete().where(
            (tables.PlayerStateRow.id == self.id) & (tables.PlayerStateRow.bot == self.bot)
        )

    async def upsert(self) -> None:
        """Upsert the player state in the database."""
        values = {
            tables.PlayerStateRow.channel_id: self.channel_id,
            tables.PlayerStateRow.volume: self.volume,
            tables.PlayerStateRow.position: self.position,
            tables.PlayerStateRow.auto_play_playlist_id: self.auto_play_playlist_id,
            tables.PlayerStateRow.text_channel_id: self.text_channel_id,
            tables.PlayerStateRow.notify_channel_id: self.notify_channel_id,
            tables.PlayerStateRow.forced_channel_id: self.forced_channel_id,
            tables.PlayerStateRow.paused: self.paused,
            tables.PlayerStateRow.repeat_current: self.repeat_current,
            tables.PlayerStateRow.repeat_queue: self.repeat_queue,
            tables.PlayerStateRow.shuffle: self.shuffle,
            tables.PlayerStateRow.auto_shuffle: self.auto_shuffle,
            tables.PlayerStateRow.auto_play: self.auto_play,
            tables.PlayerStateRow.playing: self.playing,
            tables.PlayerStateRow.effect_enabled: self.effect_enabled,
            tables.PlayerStateRow.self_deaf: self.self_deaf,
            tables.PlayerStateRow.current: self.current,
            tables.PlayerStateRow.queue: self.queue,
            tables.PlayerStateRow.history: self.history,
            tables.PlayerStateRow.effects: self.effects,
            tables.PlayerStateRow.extras: self.extras,
        }
        player = (
            await tables.PlayerStateRow.objects()
            .output(load_json=True)
            .get_or_create(
                (tables.PlayerStateRow.id == self.id) & (tables.PlayerStateRow.bot == self.bot), defaults=values
            )
        )
        if not player._was_created:
            await tables.PlayerStateRow.update(values).where(
                (tables.PlayerStateRow.id == self.id) & (tables.PlayerStateRow.bot == self.bot)
            )

    async def save(self) -> None:
        """Save the player state to the database."""
        await self.upsert()

    @classmethod
    async def get(cls, bot_id: int, guild_id: int) -> PlayerStateModel | None:
        """Get the player state from the database.

        Parameters
        ----------
        bot_id : int
            The bot ID.
        guild_id : int
            The guild ID.

        Returns
        -------
        PlayerStateModel | None
            The player state if found, otherwise None.
        """
        player = (
            await tables.PlayerStateRow.select()
            .output(load_json=True)
            .where((tables.PlayerStateRow.id == guild_id) & (tables.PlayerStateRow.bot == bot_id))
        )
        if player:
            return cls(**player[0])

        return None


@dataclass(eq=True)
class PlayerModel:
    id: int
    bot: int
    forced_channel_id: int | None = None
    volume: int = 100
    max_volume: int = 1000
    auto_play_playlist_id: int = 1
    text_channel_id: int | None = None
    notify_channel_id: int | None = None
    repeat_current: bool = False
    repeat_queue: bool = False
    shuffle: bool = True
    auto_shuffle: bool = False
    auto_play: bool = True
    self_deaf: bool = True
    effects: dict = field(default_factory=dict)
    extras: dict = field(default_factory=dict)
    empty_queue_dc: TimedFeature = field(default_factory=TimedFeature)
    alone_dc: TimedFeature = field(default_factory=TimedFeature)
    alone_pause: TimedFeature = field(default_factory=TimedFeature)
    dj_users: set = field(default_factory=set)
    dj_roles: set = field(default_factory=set)

    def __post_init__(self):
        if isinstance(self.extras, str):
            self.extras = ujson.loads(self.extras)
        if isinstance(self.empty_queue_dc, str):
            self.empty_queue_dc = TimedFeature(**ujson.loads(self.empty_queue_dc))
        if isinstance(self.alone_dc, str):
            self.alone_dc = TimedFeature(**ujson.loads(self.alone_dc))
        if isinstance(self.alone_pause, str):
            self.alone_pause = TimedFeature(**ujson.loads(self.alone_pause))
        if isinstance(self.effects, str):
            self.effects = ujson.loads(self.effects)
        if isinstance(self.dj_users, str):
            self.dj_users = ujson.loads(self.dj_users)
        if isinstance(self.dj_roles, str):
            self.dj_roles = ujson.loads(self.dj_roles)

        self.dj_users = set(self.dj_users)
        self.dj_roles = set(self.dj_roles)

    async def delete(self) -> None:
        """Delete the player from the database."""
        await tables.PlayerRow.delete().where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))

    async def upsert(self) -> None:
        """Upsert the player in the database."""
        values = {
            tables.PlayerRow.forced_channel_id: self.forced_channel_id,
            tables.PlayerRow.volume: self.volume,
            tables.PlayerRow.max_volume: self.max_volume,
            tables.PlayerRow.auto_play_playlist_id: self.auto_play_playlist_id,
            tables.PlayerRow.text_channel_id: self.text_channel_id,
            tables.PlayerRow.notify_channel_id: self.notify_channel_id,
            tables.PlayerRow.repeat_current: self.repeat_current,
            tables.PlayerRow.repeat_queue: self.repeat_queue,
            tables.PlayerRow.shuffle: self.shuffle,
            tables.PlayerRow.auto_shuffle: self.auto_shuffle,
            tables.PlayerRow.auto_play: self.auto_play,
            tables.PlayerRow.self_deaf: self.self_deaf,
            tables.PlayerRow.extras: self.extras,
            tables.PlayerRow.empty_queue_dc: self.empty_queue_dc.to_dict(),
            tables.PlayerRow.alone_dc: self.alone_dc.to_dict(),
            tables.PlayerRow.alone_pause: self.alone_pause.to_dict(),
            tables.PlayerRow.effects: self.effects,
            tables.PlayerRow.dj_users: list(self.dj_users),
            tables.PlayerRow.dj_roles: list(self.dj_roles),
        }
        player = (
            await tables.PlayerRow.objects()
            .output(load_json=True)
            .get_or_create((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot), defaults=values)
        )
        if not player._was_created:
            await tables.PlayerRow.update(values).where(
                (tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot)
            )

    async def save(self) -> None:
        """Save the player to the database."""
        await self.upsert()

    @classmethod
    async def get(cls, bot_id: int, guild_id: int) -> PlayerModel | None:
        """Get the player from the database.

        Parameters
        ----------
        bot_id : int
            The bot ID.
        guild_id : int
            The guild ID.

        Returns
        -------
        PlayerModel | None
            The player if found, otherwise None.
        """
        player = (
            await tables.PlayerRow.select()
            .output(load_json=True)
            .where((tables.PlayerRow.forced_channel_id == guild_id) & (tables.PlayerRow.bot == bot_id))
        ).first()

        if player:
            return cls(**player.to_dict())

        return None

    async def get_or_create(self) -> PlayerModel:
        """Get the player from the database.

        Returns
        -------
        PlayerModel
            The player if found, otherwise None.
        """

        values = {
            tables.PlayerRow.forced_channel_id: self.forced_channel_id,
            tables.PlayerRow.volume: self.volume,
            tables.PlayerRow.max_volume: self.max_volume,
            tables.PlayerRow.auto_play_playlist_id: self.auto_play_playlist_id,
            tables.PlayerRow.text_channel_id: self.text_channel_id,
            tables.PlayerRow.notify_channel_id: self.notify_channel_id,
            tables.PlayerRow.repeat_current: self.repeat_current,
            tables.PlayerRow.repeat_queue: self.repeat_queue,
            tables.PlayerRow.shuffle: self.shuffle,
            tables.PlayerRow.auto_shuffle: self.auto_shuffle,
            tables.PlayerRow.auto_play: self.auto_play,
            tables.PlayerRow.self_deaf: self.self_deaf,
            tables.PlayerRow.extras: self.extras,
            tables.PlayerRow.empty_queue_dc: self.empty_queue_dc.to_dict(),
            tables.PlayerRow.alone_dc: self.alone_dc.to_dict(),
            tables.PlayerRow.alone_pause: self.alone_pause.to_dict(),
            tables.PlayerRow.effects: self.effects,
            tables.PlayerRow.dj_users: list(self.dj_users),
            tables.PlayerRow.dj_roles: list(self.dj_roles),
        }
        output = (
            await tables.PlayerRow.objects()
            .output(load_json=True)
            .get_or_create((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot), defaults=values)
        )
        if not output._was_created:
            self.forced_channel_id = output.forced_channel_id
            self.volume = output.volume
            self.max_volume = output.max_volume
            self.auto_play_playlist_id = output.auto_play_playlist_id
            self.text_channel_id = output.text_channel_id
            self.notify_channel_id = output.notify_channel_id
            self.repeat_current = output.repeat_current
            self.repeat_queue = output.repeat_queue
            self.shuffle = output.shuffle
            self.auto_shuffle = output.auto_shuffle
            self.auto_play = output.auto_play
            self.self_deaf = output.self_deaf
            self.extras = output.extras
            self.empty_queue_dc = TimedFeature(**output.empty_queue_dc)
            self.alone_dc = TimedFeature(**output.alone_dc)
            self.alone_pause = TimedFeature(**output.alone_pause)
            self.effects = output.effects
            self.dj_users = set(output.dj_users)
            self.dj_roles = set(output.dj_roles)
        return self

    async def update_volume(self):
        """Update the volume of the player."""
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.volume)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.volume = player[0]["volume"]

    async def update_max_volume(self):
        """Update the max volume of the player."""
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.max_volume)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.max_volume = player[0]["max_volume"]

    async def update_auto_play_playlist_id(self) -> PlayerModel:
        """Update the auto play playlist ID of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.auto_play_playlist_id)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.auto_play_playlist_id = player[0]["auto_play_playlist_id"]
        return self

    async def update_text_channel_id(self) -> PlayerModel:
        """Update the text channel ID of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.text_channel_id)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.text_channel_id = player[0]["text_channel_id"]
        return self

    async def update_notify_channel_id(self) -> PlayerModel:
        """Update the notify channel ID of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.notify_channel_id)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.notify_channel_id = player[0]["notify_channel_id"]
        return self

    async def update_forced_channel_id(self) -> PlayerModel:
        """Update the forced channel ID of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.forced_channel_id)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.forced_channel_id = player[0]["forced_channel_id"]
        return self

    async def update_repeat_current(self) -> PlayerModel:
        """Update the repeat current of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.repeat_current)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.repeat_current = player[0]["repeat_current"]
        return self

    async def update_repeat_queue(self) -> PlayerModel:
        """Update the repeat queue of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.repeat_queue)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.repeat_queue = player["repeat_queue"]
        return self

    async def update_shuffle(self) -> PlayerModel:
        """Update the shuffle of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.shuffle)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.shuffle = player[0]["shuffle"]
        return self

    async def update_auto_shuffle(self) -> PlayerModel:
        """Update the auto shuffle of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.auto_shuffle)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.auto_shuffle = player[0]["auto_shuffle"]
        return self

    async def update_auto_play(self) -> PlayerModel:
        """Update the auto play of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.auto_play)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.auto_play = player[0]["auto_play"]
        return self

    async def update_self_deaf(self) -> PlayerModel:
        """Update the self deaf of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.self_deaf)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            self.self_deaf = player[0]["self_deaf"]
        return self

    async def update_extras(self) -> PlayerModel:
        """Update the extras of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.extras)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            if isinstance(player[0]["extras"], str):
                self.extras = ujson.loads(player[0]["extras"])
            else:
                self.extras = player[0]["extras"]
        return self

    async def update_effects(self) -> PlayerModel:
        """Update the effects of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.effects)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            if isinstance(player[0]["effects"], str):
                self.effects = ujson.loads(player[0]["effects"])
            else:
                self.effects = player[0]["effects"]
        return self

    async def update_empty_queue_dc(self) -> PlayerModel:
        """Update the empty queue dc of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.empty_queue_dc)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            if isinstance(player[0]["empty_queue_dc"], str):
                self.empty_queue_dc = TimedFeature(**ujson.loads(player[0]["empty_queue_dc"]))
            else:
                self.empty_queue_dc = TimedFeature(**player[0]["empty_queue_dc"])
        return self

    async def update_alone_dc(self) -> PlayerModel:
        """Update the alone dc of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.alone_dc)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            if isinstance(player[0]["alone_dc"], str):
                self.alone_dc = TimedFeature(**ujson.loads(player[0]["alone_dc"]))
            else:
                self.alone_dc = TimedFeature(**player[0]["alone_dc"])
        return self

    async def update_alone_pause(self) -> PlayerModel:
        """Update the alone pause of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.alone_pause)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            if isinstance(player[0]["alone_pause"], str):
                self.alone_pause = TimedFeature(**ujson.loads(player[0]["alone_pause"]))
            else:
                self.alone_pause = TimedFeature(**player[0]["alone_pause"])
        return self

    async def dj_users_update(self) -> PlayerModel:
        """Update the dj users of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.dj_users)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            if isinstance(player[0]["dj_users"], str):
                self.dj_users = set(ujson.loads(player[0]["dj_users"]))
            else:
                self.dj_users = set(player[0]["dj_users"])
        return self

    async def dj_roles_update(self) -> PlayerModel:
        """Update the dj roles of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        player = (
            await tables.PlayerRow.select(tables.PlayerRow.dj_roles)
            .output(load_json=True)
            .where((tables.PlayerRow.id == self.id) & (tables.PlayerRow.bot == self.bot))
        )
        if player:
            if isinstance(player[0]["dj_roles"], str):
                self.dj_roles = set(ujson.loads(player[0]["dj_roles"]))
            else:
                self.dj_roles = set(player[0]["dj_roles"])
        return self

    async def dj_users_add(self, *users: discord.Member) -> PlayerModel:
        """Add dj users to the player.

        Parameters
        ----------
        users : discord.Member
            The users to add.

        Returns
        -------
        PlayerModel
            The player.
        """
        await self.dj_users_update()
        if not users:
            return self
        self.dj_users = self.dj_users.union([u.id for u in users])
        await self.dj_users_cleanup(users[0].guild, lazy=True)
        await self.save()
        return self

    async def dj_roles_add(self, *roles: discord.Role) -> PlayerModel:
        """Add dj roles to the player.

        Parameters
        ----------
        roles : discord.Role
            The roles to add.

        Returns
        -------
        PlayerModel
            The player.
        """
        await self.dj_roles_update()
        if not roles:
            return self
        self.dj_roles = self.dj_roles.union([r.id for r in roles])
        await self.dj_roles_cleanup(roles[0].guild, lazy=True)
        await self.save()
        return self

    async def dj_users_remove(self, *users: discord.Member) -> PlayerModel:
        """Remove dj users from the player.

        Parameters
        ----------
        users : discord.Member
            The users to add.

        Returns
        -------
        PlayerModel
            The player.
        """
        await self.dj_users_update()
        if not users:
            return self
        self.dj_users.difference_update({u.id for u in users})
        await self.dj_users_cleanup(users[0].guild, lazy=True)
        await self.save()
        return self

    async def dj_roles_remove(self, *roles: discord.Role) -> PlayerModel:
        """Remove dj roles from the player.

        Parameters
        ----------
        roles : discord.Role
            The roles to add.

        Returns
        -------
        PlayerModel
            The player
        """
        await self.dj_roles_update()
        if not roles:
            return self
        self.dj_roles.difference_update({r.id for r in roles if r})
        await self.dj_roles_cleanup(roles[0].guild, lazy=True)
        await self.save()
        return self

    async def dj_users_cleanup(self, guild: discord.Guild, lazy: bool = False) -> PlayerModel:
        """Cleanup the dj users of the player.

        Parameters
        ----------
        guild : discord.Guild
            The guild to cleanup.
        lazy : bool
            Whether to do a lazy cleanup.

        Returns
        -------
        PlayerModel
            The player.
        """
        if not lazy:
            await self.dj_users_update()
        self.dj_users = {u for u in self.dj_users if guild.get_member(u)}
        if not lazy:
            await self.save()
        return self

    async def dj_roles_cleanup(self, guild: discord.Guild, lazy: bool = False) -> PlayerModel:
        """Cleanup the dj roles of the player.

        Parameters
        ----------
        guild : discord.Guild
            The guild to cleanup.
        lazy : bool
            Whether to do a lazy cleanup.

        Returns
        -------
        PlayerModel
            The player.
        """
        if not lazy:
            await self.dj_roles_update()
        self.dj_roles = {r for r in self.dj_roles if guild.get_role(r)}
        if not lazy:
            await self.save()
        return self

    async def dj_users_reset(self) -> PlayerModel:
        """Reset the dj users of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        self.dj_users = set()
        await self.save()
        return self

    async def dj_roles_reset(self) -> PlayerModel:
        """Reset the dj roles of the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        self.dj_roles = set()
        await self.save()
        return self

    async def is_dj(
        self,
        user: discord.Member,
        *,
        additional_role_ids: list = None,
        additional_user_ids: list = None,
        bot: BotT = None,
    ) -> bool:

        """Check if a user is a dj.

        Parameters
        ----------
        user : discord.Member
            The user to check.
        additional_role_ids : list
            The additional dj role ids to check.
        additional_user_ids : list
            The additional dj user ids to check.
        bot : BotT
            The bot instance to check for owners, admins or mods.

        Returns
        -------
        bool
            Whether the user is a dj.
        """
        if additional_user_ids and user.id in additional_user_ids:
            return True
        if additional_role_ids and await asyncstdlib.any(r.id in additional_role_ids for r in user.roles):
            return True

        if __ := user.guild:
            if hasattr(bot, "is_owner") and await bot.is_owner(user):  # type: ignore
                return True
            if hasattr(bot, "is_admin") and await bot.is_admin(user):
                return True
            if hasattr(bot, "is_mod") and await bot.is_mod(user):
                return True

        await self.dj_users_update()
        await self.dj_users_cleanup(guild=user.guild, lazy=True)
        if user.id in self.dj_users:
            return True
        await self.dj_roles_update()
        await self.dj_roles_cleanup(guild=user.guild, lazy=True)
        if await asyncstdlib.any(r.id in self.dj_roles for r in user.roles):
            return True
        if not self.dj_users and not self.dj_roles:
            return True
        return False

    async def fetch_volume(self) -> int:
        """Fetch the volume of the player.

        Returns
        -------
        int
            The volume.
        """
        await self.update_volume()
        return self.volume

    async def fetch_repeat_current(self) -> bool:
        """Fetch the repeat current of the player.

        Returns
        -------
        bool
            The repeat current.
        """
        await self.update_repeat_current()
        return self.repeat_current

    async def fetch_repeat_queue(self) -> bool:
        """Fetch the repeat queue of the player.

        Returns
        -------
        bool
            The repeat queue.
        """
        await self.update_repeat_queue()
        return self.repeat_queue

    async def fetch_shuffle(self) -> bool | None:
        """Fetch the shuffle of the player.

        Returns
        -------
        bool | None
            The shuffle.
        """
        await self.update_shuffle()
        return self.shuffle

    async def fetch_auto_shuffle(self) -> bool:
        """Fetch the auto shuffle of the player.

        Returns
        -------
        bool
            The auto shuffle.
        """
        await self.update_auto_shuffle()
        return self.auto_shuffle

    async def fetch_auto_play(self) -> bool:
        """Fetch the auto play of the player.

        Returns
        -------
        bool
            The auto play.
        """
        await self.update_auto_play()
        return self.auto_play

    async def fetch_self_deaf(self) -> bool:
        """Fetch the self deaf of the player.

        Returns
        -------
        bool
            The self deaf.
        """
        await self.update_self_deaf()
        return self.self_deaf

    async def fetch_extras(self) -> dict:
        """Fetch the extras of the player.

        Returns
        -------
        dict
            The extras.
        """
        await self.update_extras()
        return self.extras

    async def fetch_effects(self) -> dict:
        """Fetch the effects of the player.

        Returns
        -------
        dict
            The effects.
        """
        await self.update_effects()
        return self.effects

    async def fetch_empty_queue_dc(self) -> TimedFeature:
        """Fetch the empty queue dc of the player.

        Returns
        -------
        TimedFeature
            The empty queue dc.
        """
        await self.update_empty_queue_dc()
        return self.empty_queue_dc

    async def fetch_alone_dc(self) -> TimedFeature:
        """Fetch the alone dc of the player.

        Returns
        -------
        TimedFeature
            The alone dc.
        """
        await self.update_alone_dc()
        return self.alone_dc

    async def fetch_alone_pause(self) -> TimedFeature:
        """Fetch the alone pause of the player.

        Returns
        -------
        TimedFeature
            The alone pause.
        """
        await self.update_alone_pause()
        return self.alone_pause

    async def fetch_max_volume(self) -> int:
        """Fetch the max volume of the player.

        Returns
        -------
        int
            The max volume.
        """
        await self.update_max_volume()
        return self.max_volume

    async def update(self) -> PlayerModel:
        """Update the player.

        Returns
        -------
        PlayerModel
            The player.
        """
        await self.get_or_create()
        return self


@dataclass(eq=True)
class EqualizerModel:
    id: int
    scope: int
    author: int
    name: str | None = None
    description: str | None = None
    band_25: int = 0.0
    band_40: int = 0.0
    band_63: int = 0.0
    band_100: int = 0.0
    band_160: int = 0.0
    band_250: int = 0.0
    band_400: int = 0.0
    band_630: int = 0.0
    band_1000: int = 0.0
    band_1600: int = 0.0
    band_2500: int = 0.0
    band_4000: int = 0.0
    band_6300: int = 0.0
    band_10000: int = 0.0
    band_16000: int = 0.0

    async def save(self) -> EqualizerModel:
        """Save the Equalizer to the database.

        Returns
        -------
        EqualizerModel
            The Equalizer.
        """
        values = {
            tables.EqualizerRow.scope: self.scope,
            tables.EqualizerRow.author: self.author,
            tables.EqualizerRow.name: self.name,
            tables.EqualizerRow.description: self.description,
            tables.EqualizerRow.band_25: self.band_25,
            tables.EqualizerRow.band_40: self.band_40,
            tables.EqualizerRow.band_63: self.band_63,
            tables.EqualizerRow.band_100: self.band_100,
            tables.EqualizerRow.band_160: self.band_160,
            tables.EqualizerRow.band_250: self.band_250,
            tables.EqualizerRow.band_400: self.band_400,
            tables.EqualizerRow.band_630: self.band_630,
            tables.EqualizerRow.band_1000: self.band_1000,
            tables.EqualizerRow.band_1600: self.band_1600,
            tables.EqualizerRow.band_2500: self.band_2500,
            tables.EqualizerRow.band_4000: self.band_4000,
            tables.EqualizerRow.band_6300: self.band_6300,
            tables.EqualizerRow.band_10000: self.band_10000,
            tables.EqualizerRow.band_16000: self.band_16000,
        }
        playlist = (
            await tables.EqualizerRow.objects()
            .output(load_json=True)
            .get_or_create(tables.EqualizerRow.id == self.id, defaults=values)
        )
        if not playlist._was_created:
            await tables.EqualizerRow.update(values).where(tables.EqualizerRow.id == self.id)
        return EqualizerModel(**playlist.to_dict())

    @classmethod
    async def get(cls, id: int) -> EqualizerModel | None:
        """Get an equalizer from the database.

        Parameters
        ----------
        id: int
            The id of the equalizer.

        Returns
        -------
        EqualizerModel | None
            The equalizer if found, else None.
        """
        equalizer = await tables.EqualizerRow.select().where(tables.EqualizerRow.id == id)
        if equalizer:
            return EqualizerModel(**equalizer.to_dict())
        return None

    async def delete(self):
        """Delete the equalizer from the database."""
        await tables.EqualizerRow.delete().where(tables.EqualizerRow.id == self.id)

    async def can_manage(self, bot: BotT, requester: discord.abc.User, guild: discord.Guild = None) -> bool:
        """Check if the requester can manage the equalizer.

        Parameters
        ----------
        bot: BotT
            The bot.
        requester: discord.abc.User
            The requester.
        guild: discord.Guild | None
            The guild.

        Returns
        -------
        bool
            If the requester can manage the equalizer.
        """
        if self.scope in BUNDLED_PLAYLIST_IDS:
            return False
        if requester.id in ((ids := getattr(bot, "owner_ids")) or ()) or requester.id == bot.owner_id:  # noqa
            return True
        elif self.scope == bot.user.id:
            return False
        return self.author == requester.id

    async def get_scope_name(self, bot: BotT, mention: bool = True, guild: discord.Guild = None) -> str:
        """Get the name of the scope.

        Parameters
        ----------
        bot: BotT
            The bot.
        mention: bool
            If the name should be mentionable.
        guild: discord.Guild | None
            The guild.

        Returns
        -------
        str
            The name of the scope.
        """
        if bot.user.id == self.scope:
            return f"(Global) {bot.user.mention}" if mention else f"(Global) {bot.user}"
        elif guild_ := bot.get_guild(self.scope):
            if guild_:
                guild = guild_
            return f"(Server) {guild.name}"
        elif guild and (channel := guild.get_channel_or_thread(self.scope)):
            return f"(Channel) {channel.mention}" if mention else f"(Channel) {channel.name}"

        elif (
            (guild := guild_ or guild)
            and (guild and (author := guild.get_member(self.scope)))
            or (author := bot.get_user(self.author))
        ):
            return f"(User) {author.mention}" if mention else f"(User) {author}"
        else:
            return f"(Invalid) {self.scope}"

    async def get_author_name(self, bot: BotT, mention: bool = True) -> str | None:
        """Get the name of the author.

        Parameters
        ----------
        bot: BotT
            The bot.
        mention: bool
            If the name should be mentionable.

        Returns
        -------
        str | None
            The name of the author.
        """
        if user := bot.get_user(self.author):
            return f"{user.mention}" if mention else f"{user}"
        return f"{self.author}"

    @asynccontextmanager
    async def to_yaml(self, guild: discord.Guild) -> Iterator[tuple[io.BytesIO, str | None]]:
        """Serialize the Equalizer to a YAML file.

        yields a tuple of (io.BytesIO, bool) where the bool is whether the playlist file was compressed using Gzip

        Parameters
        ----------
        guild: discord.Guild
            The guild.

        Yields
        -------
        tuple[io.BytesIO, str | None]
            The YAML file and the compression type.

        """
        data = {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "description": self.description,
            "scope": self.scope,
            "bands": {
                "25": self.band_25,
                "40": self.band_40,
                "63": self.band_63,
                "100": self.band_100,
                "160": self.band_160,
                "250": self.band_250,
                "400": self.band_400,
                "630": self.band_630,
                "1000": self.band_1000,
                "1600": self.band_1600,
                "2500": self.band_2500,
                "4000": self.band_4000,
                "6300": self.band_6300,
                "10000": self.band_10000,
                "16000": self.band_16000,
            },
        }
        compression = None
        with io.BytesIO() as bio:
            yaml.safe_dump(data, bio, default_flow_style=False, sort_keys=False, encoding="utf-8")
            bio.seek(0)
            LOGGER.debug(f"SIZE UNCOMPRESSED EQ ({self.name}): {sys.getsizeof(bio)}")
            if sys.getsizeof(bio) > guild.filesize_limit:
                with io.BytesIO() as bio:
                    if BROTLI_ENABLED:
                        compression = "brotli"
                        bio.write(brotli.compress(yaml.dump(data, encoding="utf-8")))
                    else:
                        compression = "gzip"
                        with gzip.GzipFile(fileobj=bio, mode="wb", compresslevel=9) as gfile:
                            yaml.safe_dump(data, gfile, default_flow_style=False, sort_keys=False, encoding="utf-8")
                    bio.seek(0)
                    LOGGER.debug(f"SIZE COMPRESSED EQ [{compression}] ({self.name}): {sys.getsizeof(bio)}")
                    yield bio, compression
                    return
            yield bio, compression

    @classmethod
    async def from_yaml(cls, context: PyLavContext, scope: int, url: str) -> EqualizerModel:
        """Deserialize a Equalizer from a YAML file.

        Parameters
        ----------
        context: PyLavContext
            The context.
        scope: int
            The scope.
        url: str
            The URL to the YAML file.

        Returns
        -------
        EqualizerModel
            The Equalizer.

        """
        try:
            async with aiohttp.ClientSession(auto_decompress=False) as session:
                async with session.get(url) as response:
                    data = await response.read()
                    data = gzip.decompress(data)
                    data = yaml.safe_load(data)
        except Exception as e:
            raise InvalidPlaylist(f"Invalid equalizer file - {e}") from e
        return cls(
            id=context.message.id,
            scope=scope,
            name=data["name"],
            author=data["author"],
            description=data["description"],
            band_25=data["bands"]["25"],
            band_40=data["bands"]["40"],
            band_63=data["bands"]["63"],
            band_100=data["bands"]["100"],
            band_160=data["bands"]["160"],
            band_250=data["bands"]["250"],
            band_400=data["bands"]["400"],
            band_630=data["bands"]["630"],
            band_1000=data["bands"]["1000"],
            band_1600=data["bands"]["1600"],
            band_2500=data["bands"]["2500"],
            band_4000=data["bands"]["4000"],
            band_6300=data["bands"]["6300"],
            band_10000=data["bands"]["10000"],
            band_16000=data["bands"]["16000"],
        )

    def to_dict(self) -> dict:
        """Serialize the Equalizer to a dict.

        Returns
        -------
        dict
            The dict representation of the Equalizer.
        """

        return {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "description": self.description,
            "scope": self.scope,
            "bands": {
                "25": self.band_25,
                "40": self.band_40,
                "63": self.band_63,
                "100": self.band_100,
                "160": self.band_160,
                "250": self.band_250,
                "400": self.band_400,
                "630": self.band_630,
                "1000": self.band_1000,
                "1600": self.band_1600,
                "2500": self.band_2500,
                "4000": self.band_4000,
                "6300": self.band_6300,
                "10000": self.band_10000,
                "16000": self.band_16000,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> EqualizerModel:
        """Deserialize a Equalizer from a dict.

        Parameters
        ----------
        data: dict
            The data to use to build the Equalizer

        Returns
        -------
        EqualizerModel
            The Equalizer
        """
        return cls(
            id=data["id"],
            scope=data["scope"],
            name=data["name"],
            author=data["author"],
            description=data["description"],
            band_25=data["bands"]["25"],
            band_40=data["bands"]["40"],
            band_63=data["bands"]["63"],
            band_100=data["bands"]["100"],
            band_160=data["bands"]["160"],
            band_250=data["bands"]["250"],
            band_400=data["bands"]["400"],
            band_630=data["bands"]["630"],
            band_1000=data["bands"]["1000"],
            band_1600=data["bands"]["1600"],
            band_2500=data["bands"]["2500"],
            band_4000=data["bands"]["4000"],
            band_6300=data["bands"]["6300"],
            band_10000=data["bands"]["10000"],
            band_16000=data["bands"]["16000"],
        )

    def to_filter(self) -> Equalizer:
        """Serialize the Equalizer to a Filter.

        Returns
        -------
        Equalizer
            The filter representation of the Equalizer
        """
        return Equalizer(
            name=self.name or "CustomEqualizer",
            levels=[
                {"band": 0, "gain": self.band_25},
                {"band": 1, "gain": self.band_40},
                {"band": 2, "gain": self.band_63},
                {"band": 3, "gain": self.band_100},
                {"band": 4, "gain": self.band_160},
                {"band": 5, "gain": self.band_250},
                {"band": 6, "gain": self.band_400},
                {"band": 7, "gain": self.band_630},
                {"band": 8, "gain": self.band_1000},
                {"band": 9, "gain": self.band_1600},
                {"band": 10, "gain": self.band_2500},
                {"band": 11, "gain": self.band_4000},
                {"band": 12, "gain": self.band_6300},
                {"band": 13, "gain": self.band_10000},
                {"band": 14, "gain": self.band_16000},
            ],
        )

    @classmethod
    def from_filter(
        cls, equalizer: Equalizer, context: PyLavContext, scope: int, description: str = None
    ) -> EqualizerModel:
        """Deserialize a Equalizer from a Filter.

        Parameters
        ----------
        equalizer: Equalizer
            The filter object
        context: PyLavContext
            The Context
        scope: int
            The scope number
        description: str
            The description of the Equalizer

        Returns
        -------
        EqualizerModel
            The EqualizerModel built from the Equalizer object
        """
        return EqualizerModel(
            id=context.message.id,
            scope=scope,
            name=equalizer.name,
            author=context.author.id,
            description=description,
            band_25=equalizer._eq[0]["gain"],
            band_40=equalizer._eq[1]["gain"],
            band_63=equalizer._eq[2]["gain"],
            band_100=equalizer._eq[3]["gain"],
            band_160=equalizer._eq[4]["gain"],
            band_250=equalizer._eq[5]["gain"],
            band_400=equalizer._eq[6]["gain"],
            band_630=equalizer._eq[7]["gain"],
            band_1000=equalizer._eq[8]["gain"],
            band_1600=equalizer._eq[9]["gain"],
            band_2500=equalizer._eq[10]["gain"],
            band_4000=equalizer._eq[11]["gain"],
            band_6300=equalizer._eq[12]["gain"],
            band_10000=equalizer._eq[13]["gain"],
            band_16000=equalizer._eq[14]["gain"],
        )
