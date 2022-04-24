from __future__ import annotations

import datetime
from dataclasses import dataclass, field

import discord
import ujson

from pylav._config import CONFIG_DIR
from pylav.sql.tables import LibConfigRow, NodeRow, PlaylistRow, QueryRow
from pylav.types import BotT


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
        if self.scope < 1000:
            return False
        if requester.id in ((ids := getattr(bot, "owner_ids")) or ()) or requester.id == bot.owner_id:  # noqa
            return True
        elif self.scope == bot.user.id:
            return False
        if (guild := bot.get_guild(self.scope)) or (guild and (channel := guild.get_channel(self.scope))):
            if guild.owner_id == requester.id:
                return True
            if hasattr(bot, "is_mod"):
                if not isinstance(requester, discord.Member):
                    requester = guild.get_member(requester.id)
                    if not requester:
                        return False
                return await bot.is_mod(requester)
            return False
        return self.author == requester.id

    async def get_scope_name(self, bot: BotT, mention: bool = True, guild: discord.Guild = None) -> str:
        if guild := bot.get_guild(self.scope):
            scope_name = f"(Server) {guild.name}"
        elif (guild and (author := guild.get_member(self.scope))) or (author := bot.get_user(self.author)):
            scope_name = f"(User) {author.mention}" if mention else f"(User) {author}"
        elif guild and (channel := guild.get_channel(self.scope)):
            scope_name = f"(Channel) {channel.mention}" if mention else f"(Channel) {channel}"
        elif bot.user.id == self.scope:
            scope_name = f"(Global) {bot.user.mention}" if mention else f"(Global) {bot.user}"
        else:
            scope_name = f"(Invalid) {self.scope}"
        return scope_name

    async def get_author_name(self, bot: BotT, mention: bool = True) -> str | None:
        if user := bot.get_user(self.author):
            if not mention:
                return f"{user}"
            return f"{user.mention}"
        return f"{self.author}"


@dataclass(eq=True)
class LibConfigModel:
    id: int = 1
    config_folder: str | None = None
    localtrack_folder: str | None = None
    java_path: str | None = None
    enable_managed_node: bool | None = None
    auto_update_managed_nodes: bool | None = None

    async def get_config_folder(self) -> str:
        response = await LibConfigRow.select(LibConfigRow.config_folder).where(LibConfigRow.id == self.id).first()
        return response["config_folder"]

    async def get_java_path(self) -> str:
        response = await LibConfigRow.select(LibConfigRow.java_path).where(LibConfigRow.id == self.id).first()
        return response["java_path"]

    async def get_enable_managed_node(self) -> bool:
        response = await LibConfigRow.select(LibConfigRow.enable_managed_node).where(LibConfigRow.id == self.id).first()
        return response["enable_managed_node"]

    async def get_auto_update_managed_nodes(self) -> bool:
        response = (
            await LibConfigRow.select(LibConfigRow.auto_update_managed_nodes).where(LibConfigRow.id == self.id).first()
        )
        return response["auto_update_managed_nodes"]

    async def get_localtrack_folder(self) -> str:
        response = await LibConfigRow.select(LibConfigRow.localtrack_folder).where(LibConfigRow.id == self.id).first()
        return response["localtrack_folder"]

    async def set_config_folder(self, value: str) -> None:
        self.config_folder = value
        await LibConfigRow.update({LibConfigRow.config_folder: value}).where(LibConfigRow.id == self.id)

    async def set_java_path(self, value: str) -> None:
        self.java_path = value
        await LibConfigRow.update({LibConfigRow.java_path: value}).where(LibConfigRow.id == self.id)

    async def set_enable_managed_node(self, value: bool) -> None:
        self.enable_managed_node = value
        await LibConfigRow.update({LibConfigRow.enable_managed_node: value}).where(LibConfigRow.id == self.id)

    async def set_auto_update_managed_nodes(self, value: bool) -> None:
        self.auto_update_managed_nodes = value
        await LibConfigRow.update({LibConfigRow.auto_update_managed_nodes: value}).where(LibConfigRow.id == self.id)

    async def set_localtrack_folder(self, value: str) -> None:
        self.localtrack_folder = value
        await LibConfigRow.update({LibConfigRow.localtrack_folder: value}).where(LibConfigRow.id == self.id)

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
        if data:
            await LibConfigRow.update(**data).where(LibConfigRow.id == self.id)
        return self

    async def delete(self) -> None:
        await LibConfigRow.delete().where(LibConfigRow.id == self.id)

    async def get_all(self) -> LibConfigModel:
        response = await LibConfigRow.select().where(LibConfigRow.id == self.id).first()
        self.config_folder = response["config_folder"]
        self.java_path = response["java_path"]
        self.enable_managed_node = response["enable_managed_node"]
        self.auto_update_managed_nodes = response["auto_update_managed_nodes"]
        self.localtrack_folder = response["localtrack_folder"]
        return self

    @classmethod
    async def get_or_create(
        cls,
        id: int,
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
                LibConfigRow.id == id,
                defaults=dict(
                    config_folder=config_folder,
                    java_path=java_path,
                    localtrack_folder=localtrack_folder,
                    enable_managed_node=enable_managed_node,
                    auto_update_managed_nodes=auto_update_managed_nodes,
                ),
            )
        )
        return cls(**r.to_dict())


@dataclass(eq=True)
class NodeModel:
    id: int
    name: str
    ssl: bool
    reconnect_attempts: int
    search_only: bool
    extras: dict

    def __post_init__(self):
        if isinstance(self.extras, str):
            self.extras = ujson.loads(self.extras)

    @classmethod
    async def from_id(cls, id: int) -> NodeModel:
        response = await NodeRow.select().where(NodeRow.id == id).first()
        return cls(**response)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ssl": self.ssl,
            "reconnect_attempts": self.reconnect_attempts,
            "search_only": self.search_only,
            "extras": self.extras,
            "name": self.name,
        }

    def get_connection_args(self) -> dict:
        if self.extras is None:
            raise ValueError("Node Connection config set")
        return {
            "unique_identifier": self.id,
            "host": self.extras["server"]["address"],
            "port": self.extras["server"]["port"],
            "password": self.extras["lavalink"]["server"]["password"],
            "name": self.name,
            "ssl": self.ssl,
            "reconnect_attempts": self.reconnect_attempts,
            "search_only": self.search_only,
            "resume_timeout": self.extras.get("resume_timeout"),
            "resume_key": self.extras.get("resume_key"),
        }

    async def save(self) -> None:
        await self.upsert()

    async def delete(self) -> None:
        await NodeRow.delete().where(NodeRow.id == self.id)

    async def upsert(self) -> None:
        values = {
            NodeRow.name: self.name,
            NodeRow.ssl: self.ssl,
            NodeRow.reconnect_attempts: self.reconnect_attempts,
            NodeRow.search_only: self.search_only,
            NodeRow.extras: self.extras,
        }
        node = await NodeRow.objects().output(load_json=True).get_or_create(NodeRow.id == self.id, defaults=values)
        if not node._was_created:
            await NodeRow.update(values).where(NodeRow.id == self.id)

    async def get_or_create(self) -> None:
        values = {
            NodeRow.name: self.name,
            NodeRow.ssl: self.ssl,
            NodeRow.reconnect_attempts: self.reconnect_attempts,
            NodeRow.search_only: self.search_only,
            NodeRow.extras: self.extras,
        }
        output = await NodeRow.objects().output(load_json=True).get_or_create(NodeRow.id == self.id, defaults=values)
        if not output._was_created:
            self.name = output.name
            self.ssl = output.ssl
            self.reconnect_attempts = output.reconnect_attempts
            self.search_only = output.search_only
            self.extras = output.extras


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
