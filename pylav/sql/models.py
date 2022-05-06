from __future__ import annotations

import datetime
import gzip
import io
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Iterator

import aiohttp
import discord
import ujson
import yaml
from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

from pylav._config import CONFIG_DIR
from pylav._logging import getLogger
from pylav.constants import BUNDLED_PLAYLIST_IDS, SUPPORTED_SOURCES
from pylav.exceptions import InvalidPlaylist
from pylav.sql.tables import BotVersionRow, LibConfigRow, NodeRow, PlayerRow, PlayerStateRow, PlaylistRow, QueryRow
from pylav.types import BotT, TimedFeatureT
from pylav.utils import PyLavContext, TimedFeature

BRACKETS: re.Pattern = re.compile(r"[\[\]]")

LOGGER = getLogger("red.PyLink.DBModels")


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

    async def save(self):
        """
        Save the playlist to the database.
        """
        values = {
            PlaylistRow.scope: self.scope,
            PlaylistRow.author: self.author,
            PlaylistRow.name: self.name,
            PlaylistRow.url: self.url,
            PlaylistRow.tracks: self.tracks,
        }
        playlist = (
            await PlaylistRow.objects().output(load_json=True).get_or_create(PlaylistRow.id == self.id, defaults=values)
        )
        if not playlist._was_created:
            await PlaylistRow.update(values).where(PlaylistRow.id == self.id)
        return PlaylistModel(**playlist.to_dict())

    @classmethod
    async def get(cls, id: int) -> PlaylistModel | None:
        """
        Get a playlist from the database.
        """
        playlist = await PlaylistRow.select().where(PlaylistRow.id == id)
        if playlist:
            return PlaylistModel(**playlist.to_dict())
        return None

    async def delete(self):
        await PlaylistRow.delete().where(PlaylistRow.id == self.id)

    async def can_manage(self, bot: BotT, requester: discord.abc.User, guild: discord.Guild = None) -> bool:
        if self.scope in BUNDLED_PLAYLIST_IDS:
            return False
        if requester.id in ((ids := getattr(bot, "owner_ids")) or ()) or requester.id == bot.owner_id:  # noqa
            return True
        elif self.scope == bot.user.id:
            return False
        channel = None
        if (guild_ := bot.get_guild(self.scope)) or (
            (guild := guild_ or guild) and (channel := guild.get_channel_or_thread(self.scope))
        ):
            if guild_:
                guild = guild_
            if guild.owner_id == requester.id:
                return True
            if hasattr(bot, "is_mod"):
                if not isinstance(requester, discord.Member):
                    requester = guild.get_member(requester.id)
                    if not requester:
                        return False
                return await bot.is_mod(requester)
            if channel and channel.permissions_for(guild.me).manage_guild:
                return True
            return False
        return self.author == requester.id

    async def get_scope_name(self, bot: BotT, mention: bool = True, guild: discord.Guild = None) -> str:
        if bot.user.id == self.scope:
            scope_name = f"(Global) {bot.user.mention}" if mention else f"(Global) {bot.user}"
        elif guild_ := bot.get_guild(self.scope):
            if guild_:
                guild = guild_
            scope_name = f"(Server) {guild.name}"
        elif guild and (channel := guild.get_channel_or_thread(self.scope)):
            scope_name = f"(Channel) {channel.mention}" if mention else f"(Channel) {channel.name}"
        elif (
            (guild := guild_ or guild)
            and (guild and (author := guild.get_member(self.scope)))
            or (author := bot.get_user(self.author))
        ):
            scope_name = f"(User) {author.mention}" if mention else f"(User) {author}"
        else:
            scope_name = f"(Invalid) {self.scope}"
        return scope_name

    async def get_author_name(self, bot: BotT, mention: bool = True) -> str | None:
        if user := bot.get_user(self.author):
            if not mention:
                return f"{user}"
            return f"{user.mention}"
        return f"{self.author}"

    async def get_name_formatted(self, with_url: bool = True) -> str:
        name = BRACKETS.sub("", self.name).strip()
        if with_url and self.url and self.url.startswith("http"):
            return f"**[{discord.utils.escape_markdown(name)}]({self.url})**"
        else:
            return f"**{discord.utils.escape_markdown(name)}**"

    @asynccontextmanager
    async def to_yaml(self, guild: discord.Guild) -> Iterator[io.BytesIO]:
        """
        Serialize the playlist to a YAML file.

        yields a tuple of (io.BytesIO, bool) where the bool is whether the playlist file was compressed using Gzip
        """
        data = {
            "name": self.name,
            "author": self.author,
            "url": self.url,
            "tracks": self.tracks,
        }

        with io.BytesIO() as bio:
            with gzip.GzipFile(fileobj=bio, mode="wb", compresslevel=9) as gfile:
                yaml.safe_dump(data, gfile, default_flow_style=False, sort_keys=False, encoding="utf-8")
            bio.seek(0)
            yield bio

    @classmethod
    async def from_yaml(cls, context: PyLavContext, scope: int, url: str) -> PlaylistModel:
        """
        Deserialize a playlist from a YAML file.
        """
        try:
            async with aiohttp.ClientSession(auto_decompress=False) as session:
                async with session.get(url) as response:
                    data = await response.read()
                    data = gzip.decompress(data)
                    data = yaml.safe_load(data)
        except Exception as e:
            raise InvalidPlaylist(f"Invalid playlist file - {e}")
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
    auto_update_managed_nodes: bool | None = None
    extras: dict = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.extras, str):
            self.extras = ujson.loads(self.extras)

    async def get_config_folder(self) -> str:
        response = (
            await LibConfigRow.select(LibConfigRow.config_folder)
            .where((LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot))
            .first()
        )
        return response["config_folder"]

    async def get_java_path(self) -> str:
        response = (
            await LibConfigRow.select(LibConfigRow.java_path)
            .where((LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot))
            .first()
        )
        return response["java_path"]

    async def get_enable_managed_node(self) -> bool:
        response = (
            await LibConfigRow.select(LibConfigRow.enable_managed_node)
            .where((LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot))
            .first()
        )
        return response["enable_managed_node"]

    async def get_auto_update_managed_nodes(self) -> bool:
        response = (
            await LibConfigRow.select(LibConfigRow.auto_update_managed_nodes)
            .where((LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot))
            .first()
        )
        return response["auto_update_managed_nodes"]

    async def get_localtrack_folder(self) -> str:
        response = (
            await LibConfigRow.select(LibConfigRow.localtrack_folder)
            .where((LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot))
            .first()
        )
        return response["localtrack_folder"]

    async def set_config_folder(self, value: str) -> None:
        self.config_folder = value
        await LibConfigRow.update({LibConfigRow.config_folder: value}).where(
            (LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot)
        )

    async def set_java_path(self, value: str) -> None:
        self.java_path = value
        await LibConfigRow.update({LibConfigRow.java_path: value}).where(
            (LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot)
        )

    async def set_enable_managed_node(self, value: bool) -> None:
        self.enable_managed_node = value
        await LibConfigRow.update({LibConfigRow.enable_managed_node: value}).where(
            (LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot)
        )

    async def set_auto_update_managed_nodes(self, value: bool) -> None:
        self.auto_update_managed_nodes = value
        await LibConfigRow.update({LibConfigRow.auto_update_managed_nodes: value}).where(
            (LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot)
        )

    async def set_localtrack_folder(self, value: str) -> None:
        self.localtrack_folder = value
        await LibConfigRow.update({LibConfigRow.localtrack_folder: value}).where(
            (LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot)
        )

    async def save(self) -> LibConfigModel:
        data = {}
        if self.config_folder:
            data["config_folder"] = self.config_folder
        if self.java_path:
            data["java_path"] = self.java_path
        if self.enable_managed_node:
            data["enable_managed_node"] = self.enable_managed_node
        if self.auto_update_managed_nodes:
            data["auto_update_managed_nodes"] = self.auto_update_managed_nodes
        if self.localtrack_folder:
            data["localtrack_folder"] = self.localtrack_folder
        if self.extras:
            data["extras"] = self.extras
        if data:
            await LibConfigRow.update(**data).where((LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot))
        return self

    async def delete(self) -> None:
        await LibConfigRow.delete().where((LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot))

    async def get_all(self) -> LibConfigModel:
        response = (
            await LibConfigRow.select().where((LibConfigRow.id == self.id) & (LibConfigRow.bot == self.bot)).first()
        )
        self.config_folder = response["config_folder"]
        self.java_path = response["java_path"]
        self.enable_managed_node = response["enable_managed_node"]
        self.auto_update_managed_nodes = response["auto_update_managed_nodes"]
        self.localtrack_folder = response["localtrack_folder"]
        self.extras = ujson.loads(response["extras"]) if isinstance(response["extras"], str) else response["extras"]
        return self

    @classmethod
    async def get_or_create(
        cls,
        id: int,
        bot: int,
        config_folder=str(CONFIG_DIR),
        localtrack_folder=str(CONFIG_DIR / "music"),
        java_path="java",
        enable_managed_node=True,
        auto_update_managed_nodes=True,
    ) -> LibConfigModel:
        r = (
            await LibConfigRow.objects()
            .output(load_json=True)
            .get_or_create(
                (LibConfigRow.id == id) & (LibConfigRow.bot == bot),
                defaults=dict(
                    config_folder=config_folder,
                    java_path=java_path,
                    localtrack_folder=localtrack_folder,
                    enable_managed_node=enable_managed_node,
                    auto_update_managed_nodes=auto_update_managed_nodes,
                    extras={},
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
        if isinstance(self.yaml, str):
            self.yaml = ujson.loads(self.yaml)
        if isinstance(self.disabled_sources, str):
            self.disabled_sources = ujson.loads(self.disabled_sources)

    @classmethod
    async def from_id(cls, id: int) -> NodeModel:
        response = await NodeRow.select().where(NodeRow.id == id).first()
        return cls(**response)

    def to_dict(self) -> dict:
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
        source = set(map(str.strip, map(str.lower, source)))
        unsupported = source - SUPPORTED_SOURCES
        if unsupported:
            raise ValueError(f"Unsupported sources: {unsupported}\nSupported sources: {SUPPORTED_SOURCES}")
        intersection = source & SUPPORTED_SOURCES
        intersection |= set(self.disabled_sources)
        self.disabled_sources = list(intersection)
        await self.save()

    async def add_source_to_exclusion_list(self, source: str):
        source = source.lower().strip()
        if source in SUPPORTED_SOURCES and source not in self.disabled_sources:
            self.disabled_sources.append(source)
            await self.save()
        raise ValueError(f"Source {source} is not supported")

    async def save(self) -> None:
        await self.upsert()

    async def delete(self) -> None:
        await NodeRow.delete().where(NodeRow.id == self.id)

    async def upsert(self) -> None:
        values = {
            NodeRow.name: self.name,
            NodeRow.ssl: self.ssl,
            NodeRow.resume_key: self.resume_key,
            NodeRow.reconnect_attempts: self.reconnect_attempts,
            NodeRow.resume_timeout: self.resume_timeout,
            NodeRow.search_only: self.search_only,
            NodeRow.managed: self.managed,
            NodeRow.extras: self.extras,
            NodeRow.yaml: self.yaml,
            NodeRow.disabled_sources: self.disabled_sources,
        }
        node = await NodeRow.objects().output(load_json=True).get_or_create(NodeRow.id == self.id, defaults=values)
        if not node._was_created:
            await NodeRow.update(values).where(NodeRow.id == self.id)

    async def get_or_create(self) -> None:
        values = {
            NodeRow.name: self.name,
            NodeRow.ssl: self.ssl,
            NodeRow.resume_key: self.resume_key,
            NodeRow.reconnect_attempts: self.reconnect_attempts,
            NodeRow.resume_timeout: self.resume_timeout,
            NodeRow.search_only: self.search_only,
            NodeRow.managed: self.managed,
            NodeRow.extras: self.extras,
            NodeRow.yaml: self.yaml,
            NodeRow.disabled_sources: self.disabled_sources,
        }
        output = await NodeRow.objects().output(load_json=True).get_or_create(NodeRow.id == self.id, defaults=values)
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
        query = await QueryRow.select().where(
            (QueryRow.identifier == identifier)
            & (QueryRow.last_updated > datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30))
        )
        data = query.to_dict()
        if query:
            return QueryModel(**data)
        return None

    async def delete(self):
        await QueryRow.delete().where(QueryRow.identifier == self.identifier)

    async def upsert(self):
        if self.last_updated is None:
            self.last_updated = datetime.datetime.now(tz=datetime.timezone.utc)
        values = {QueryRow.tracks: self.tracks, QueryRow.last_updated: self.last_updated, QueryRow.name: self.name}
        query = (
            await QueryRow.objects()
            .output(load_json=True)
            .get_or_create(
                (QueryRow.identifier == self.identifier)
                & (
                    QueryRow.last_updated
                    > datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30)
                ),
                defaults=values,
            )
        )
        if not query._was_created:
            await QueryRow.update(values).where(QueryRow.identifier == self.identifier)

    async def save(self):
        await self.upsert()


@dataclass(eq=True)
class BotVersion:
    bot: int
    version: str | LegacyVersion | Version

    def __post_init__(self):
        if isinstance(self.version, str):
            self.version = parse_version(self.version)  # type: ignore

    async def get_or_create(self) -> BotVersion:
        values = {
            BotVersionRow.version: f"{self.version}",
        }
        output = (
            await BotVersionRow.objects()
            .output(load_json=True)
            .get_or_create(BotVersionRow.bot == self.bot, defaults=values)
        )
        if not output._was_created:
            self.version = parse_version(output.version)
        return self

    async def upsert(self) -> None:
        values = {
            BotVersionRow.version: f"{self.version}",
        }
        node = (
            await BotVersionRow.objects()
            .output(load_json=True)
            .get_or_create(BotVersionRow.bot == self.bot, defaults=values)
        )
        if not node._was_created:
            await BotVersionRow.update(values).where(BotVersionRow.bot == self.bot)

    async def save(self) -> None:
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

    paused: bool
    repeat_current: bool
    repeat_queue: bool
    shuffle: bool
    auto_play: bool
    playing: bool
    effect_enabled: bool
    self_deaf: bool

    current: dict | None
    queue: dict
    history: dict
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
        await PlayerStateRow.delete().where((PlayerStateRow.id == self.id) & (PlayerStateRow.bot == self.bot))

    async def upsert(self) -> None:

        values = {
            PlayerStateRow.channel_id: self.channel_id,
            PlayerStateRow.volume: self.volume,
            PlayerStateRow.position: self.position,
            PlayerStateRow.auto_play_playlist_id: self.auto_play_playlist_id,
            PlayerStateRow.text_channel_id: self.text_channel_id,
            PlayerStateRow.notify_channel_id: self.notify_channel_id,
            PlayerStateRow.paused: self.paused,
            PlayerStateRow.repeat_current: self.repeat_current,
            PlayerStateRow.repeat_queue: self.repeat_queue,
            PlayerStateRow.shuffle: self.shuffle,
            PlayerStateRow.auto_play: self.auto_play,
            PlayerStateRow.playing: self.playing,
            PlayerStateRow.effect_enabled: self.effect_enabled,
            PlayerStateRow.self_deaf: self.self_deaf,
            PlayerStateRow.current: self.current,
            PlayerStateRow.queue: self.queue,
            PlayerStateRow.history: self.history,
            PlayerStateRow.effects: self.effects,
            PlayerStateRow.extras: self.extras,
        }
        player = (
            await PlayerStateRow.objects()
            .output(load_json=True)
            .get_or_create((PlayerStateRow.id == self.id) & (PlayerStateRow.bot == self.bot), defaults=values)
        )
        if not player._was_created:
            await PlayerStateRow.update(values).where((PlayerStateRow.id == self.id) & (PlayerStateRow.bot == self.bot))

    async def save(self) -> None:
        await self.upsert()

    @classmethod
    async def get(cls, bot_id: int, guild_id: int) -> PlayerStateModel | None:
        player = (
            await PlayerStateRow.select()
            .output(load_json=True)
            .where((PlayerStateRow.channel_id == guild_id) & (PlayerStateRow.bot == bot_id))
        ).first()

        if player:
            return cls(**player.to_dict())

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
    shuffle: bool = False
    auto_play: bool = True
    self_deaf: bool = True
    extras: dict = field(default_factory=dict)
    empty_queue_dc: TimedFeatureT = field(default_factory=dict)
    alone_dc: TimedFeatureT = field(default_factory=dict)
    alone_pause: TimedFeatureT = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.extras, str):
            self.extras = ujson.loads(self.extras)
        if isinstance(self.empty_queue_dc, str):
            self.empty_queue_dc = ujson.loads(self.empty_queue_dc)
        if isinstance(self.alone_dc, str):
            self.alone_dc = ujson.loads(self.alone_dc)
        if isinstance(self.alone_pause, str):
            self.alone_pause = ujson.loads(self.alone_pause)

    async def delete(self) -> None:
        await PlayerRow.delete().where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))

    async def upsert(self) -> None:

        values = {
            PlayerRow.forced_channel_id: self.forced_channel_id,
            PlayerRow.volume: self.volume,
            PlayerRow.max_volume: self.max_volume,
            PlayerRow.auto_play_playlist_id: self.auto_play_playlist_id,
            PlayerRow.text_channel_id: self.text_channel_id,
            PlayerRow.notify_channel_id: self.notify_channel_id,
            PlayerRow.repeat_current: self.repeat_current,
            PlayerRow.repeat_queue: self.repeat_queue,
            PlayerRow.shuffle: self.shuffle,
            PlayerRow.auto_play: self.auto_play,
            PlayerRow.self_deaf: self.self_deaf,
            PlayerRow.extras: self.extras,
            PlayerRow.empty_queue_dc: self.empty_queue_dc,
            PlayerRow.alone_dc: self.alone_dc,
            PlayerRow.alone_pause: self.alone_pause,
        }
        player = (
            await PlayerRow.objects()
            .output(load_json=True)
            .get_or_create((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot), defaults=values)
        )
        if not player._was_created:
            await PlayerRow.update(values).where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))

    async def save(self) -> None:
        await self.upsert()

    @classmethod
    async def get(cls, bot_id: int, guild_id: int) -> PlayerModel | None:
        player = (
            await PlayerRow.select()
            .output(load_json=True)
            .where((PlayerRow.forced_channel_id == guild_id) & (PlayerRow.bot == bot_id))
        ).first()

        if player:
            return cls(**player.to_dict())

        return None

    async def get_or_create(self) -> PlayerModel:
        values = {
            PlayerRow.forced_channel_id: self.forced_channel_id,
            PlayerRow.volume: self.volume,
            PlayerRow.max_volume: self.max_volume,
            PlayerRow.auto_play_playlist_id: self.auto_play_playlist_id,
            PlayerRow.text_channel_id: self.text_channel_id,
            PlayerRow.notify_channel_id: self.notify_channel_id,
            PlayerRow.repeat_current: self.repeat_current,
            PlayerRow.repeat_queue: self.repeat_queue,
            PlayerRow.shuffle: self.shuffle,
            PlayerRow.auto_play: self.auto_play,
            PlayerRow.self_deaf: self.self_deaf,
            PlayerRow.extras: self.extras,
            PlayerRow.empty_queue_dc: self.empty_queue_dc,
            PlayerRow.alone_dc: self.alone_dc,
            PlayerRow.alone_pause: self.alone_pause,
        }
        output = (
            await PlayerRow.objects()
            .output(load_json=True)
            .get_or_create((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot), defaults=values)
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
            self.auto_play = output.auto_play
            self.self_deaf = output.self_deaf
            self.extras = output.extras
            self.empty_queue_dc = output.empty_queue_dc
            self.alone_dc = output.alone_dc
            self.alone_pause = output.alone_pause
        return self

    async def update_volume(self):
        player = (
            await PlayerRow.select(PlayerRow.volume)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            self.volume = player[0]["volume"]

    async def update_max_volume(self):
        player = (
            await PlayerRow.select(PlayerRow.max_volume)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            self.max_volume = player[0]["max_volume"]

    async def update_auto_play_playlist_id(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.auto_play_playlist_id)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            self.auto_play_playlist_id = player[0]["auto_play_playlist_id"]
        return self

    async def update_text_channel_id(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.text_channel_id)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            self.text_channel_id = player[0]["text_channel_id"]
        return self

    async def update_notify_channel_id(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.notify_channel_id)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            self.notify_channel_id = player[0]["notify_channel_id"]
        return self

    async def update_forced_channel_id(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.forced_channel_id)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            self.forced_channel_id = player[0]["forced_channel_id"]
        return self

    async def update_repeat_current(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.repeat_current)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            self.repeat_current = player[0]["repeat_current"]
        return self

    async def update_repeat_queue(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.repeat_queue)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            self.repeat_queue = player["repeat_queue"]
        return self

    async def update_shuffle(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.shuffle)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            self.shuffle = player[0]["shuffle"]
        return self

    async def update_auto_play(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.auto_play)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            self.auto_play = player[0]["auto_play"]
        return self

    async def update_self_deaf(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.self_deaf)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            self.self_deaf = player[0]["self_deaf"]
        return self

    async def update_extras(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.extras)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            if isinstance(player[0]["extras"], str):
                self.extras = ujson.loads(player[0]["extras"])
            else:
                self.extras = player[0]["extras"]
        return self

    async def update_empty_queue_dc(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.empty_queue_dc)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            if isinstance(player[0]["empty_queue_dc"], str):
                self.empty_queue_dc = ujson.loads(player[0]["empty_queue_dc"])
            else:
                self.empty_queue_dc = player[0]["empty_queue_dc"]
        return self

    async def update_alone_dc(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.alone_dc)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            if isinstance(player[0]["alone_dc"], str):
                self.alone_dc = ujson.loads(player[0]["alone_dc"])
            else:
                self.alone_dc = player[0]["alone_dc"]
        return self

    async def update_alone_pause(self) -> PlayerModel:
        player = (
            await PlayerRow.select(PlayerRow.alone_pause)
            .output(load_json=True)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        )
        if player:
            if isinstance(player[0]["alone_pause"], str):
                self.alone_pause = ujson.loads(player[0]["alone_pause"])
            else:
                self.alone_pause = player[0]["alone_pause"]
        return self

    async def fetch_volume(self) -> int:
        await self.update_volume()
        return self.volume

    async def fetch_repeat_current(self) -> bool:
        await self.update_repeat_current()
        return self.repeat_current

    async def fetch_repeat_queue(self) -> bool:
        await self.update_repeat_queue()
        return self.repeat_queue

    async def fetch_shuffle(self) -> bool:
        await self.update_shuffle()
        return self.shuffle

    async def fetch_auto_play(self) -> bool:
        await self.update_auto_play()
        return self.auto_play

    async def fetch_self_deaf(self) -> bool:
        await self.update_self_deaf()
        return self.self_deaf

    async def fetch_extras(self) -> dict:
        await self.update_extras()
        return self.extras

    async def fetch_empty_queue_dc(self) -> TimedFeature:
        await self.update_empty_queue_dc()
        return TimedFeature(**self.empty_queue_dc)

    async def fetch_alone_dc(self) -> TimedFeature:
        await self.update_alone_dc()
        return TimedFeature(**self.alone_dc)

    async def fetch_alone_pause(self) -> TimedFeature:
        await self.update_alone_pause()
        return TimedFeature(**self.alone_pause)

    async def fetch_max_volume(self) -> int:
        await self.update_max_volume()
        return self.max_volume
