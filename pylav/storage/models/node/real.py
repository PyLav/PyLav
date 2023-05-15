from __future__ import annotations

from dataclasses import dataclass

from piccolo.querystring import QueryString

from pylav.compat import json
from pylav.constants.builtin_nodes import BUNDLED_NODES_IDS_HOST_MAPPING
from pylav.constants.config import JAVA_EXECUTABLE
from pylav.constants.node import NODE_DEFAULT_SETTINGS
from pylav.constants.node_features import SUPPORTED_FEATURES, SUPPORTED_SOURCES
from pylav.extension.bundled_node.utils import get_jar_ram_actual
from pylav.helpers.singleton import SingletonCachedByKey
from pylav.storage.database.cache.decodators import maybe_cached
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.nodes import NodeRow, Sessions
from pylav.type_hints.dict_typing import JSON_DICT_TYPE


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class Node(CachedModel, metaclass=SingletonCachedByKey):
    id: int

    def get_cache_key(self) -> str:
        return f"{self.id}"

    @maybe_cached
    async def exists(self) -> bool:
        """Check if the node exists in the database.

        Returns
        -------
        bool
            Whether the node exists in the database.
        """
        return await NodeRow.exists().where(NodeRow.id == self.id)

    async def delete(self) -> None:
        """Delete the node from the database"""
        await NodeRow.delete().where(NodeRow.id == self.id)
        await self.invalidate_cache()

    @maybe_cached
    async def fetch_all(self) -> JSON_DICT_TYPE:
        data = await NodeRow.select().where(NodeRow.id == self.id).first().output(load_json=True, nested=True)
        return data or {
            "id": self.id,
            "name": NodeRow.name.default,
            "ssl": NodeRow.ssl.default,
            "resume_timeout": NodeRow.resume_timeout.default,
            "reconnect_attempts": NodeRow.reconnect_attempts.default,
            "search_only": NodeRow.search_only.default,
            "managed": NodeRow.managed.default,
            "extras": json.loads(NodeRow.extras.default),
            "yaml": json.loads(NodeRow.yaml.default),
            "disabled_sources": NodeRow.disabled_sources.default,
        }

    @maybe_cached
    async def fetch_name(self) -> str | None:
        """Fetch the node from the database.

        Returns
        -------
        str
            The node's name.
        """
        data = (
            await NodeRow.select(NodeRow.name).where(NodeRow.id == self.id).first().output(load_json=True, nested=True)
        )
        return data["name"] if data else None

    async def update_name(self, name: str) -> None:
        """Update the node's name in the database"""
        await NodeRow.insert(NodeRow(id=self.id, name=name)).on_conflict(
            action="DO UPDATE", target=NodeRow.id, values=[NodeRow.name]
        )
        await self.update_cache((self.fetch_name, name), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_ssl(self) -> bool:
        """Fetch the node's ssl setting from the database.

        Returns
        -------
        bool
            The node's ssl setting.
        """
        data = (
            await NodeRow.select(NodeRow.ssl).where(NodeRow.id == self.id).first().output(load_json=True, nested=True)
        )
        return data["ssl"] if data else NodeRow.ssl.default

    async def update_ssl(self, ssl: bool) -> None:
        """Update the node's ssl setting in the database"""
        await NodeRow.insert(NodeRow(id=self.id, ssl=ssl)).on_conflict(
            action="DO UPDATE", target=NodeRow.id, values=[NodeRow.ssl]
        )
        await self.update_cache((self.fetch_ssl, ssl), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_resume_timeout(self) -> int:
        """Fetch the node's resume timeout from the database.

        Returns
        -------
        int
            The node's resume timeout.
        """
        data = (
            await NodeRow.select(NodeRow.resume_timeout)
            .where(NodeRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return data["resume_timeout"] if data else NodeRow.resume_timeout.default

    async def update_resume_timeout(self, resume_timeout: int) -> None:
        """Update the node's resume timeout in the database"""
        await NodeRow.insert(NodeRow(id=self.id, resume_timeout=resume_timeout)).on_conflict(
            action="DO UPDATE", target=NodeRow.id, values=[NodeRow.resume_timeout]
        )
        await self.update_cache((self.fetch_resume_timeout, resume_timeout), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_reconnect_attempts(self) -> int:
        """Fetch the node's reconnect attempts from the database.

        Returns
        -------
        int
            The node's reconnect attempts.
        """
        data = (
            await NodeRow.select(NodeRow.reconnect_attempts)
            .where(NodeRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return data["reconnect_attempts"] if data else NodeRow.reconnect_attempts.default

    async def update_reconnect_attempts(self, reconnect_attempts: int) -> None:
        """Update the node's reconnect attempts in the database"""
        await NodeRow.insert(NodeRow(id=self.id, reconnect_attempts=reconnect_attempts)).on_conflict(
            action="DO UPDATE", target=NodeRow.id, values=[NodeRow.reconnect_attempts]
        )
        await self.update_cache((self.fetch_reconnect_attempts, reconnect_attempts), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_search_only(self) -> bool:
        """Fetch the node's search only setting from the database.

        Returns
        -------
        bool
            The node's search only setting.
        """
        data = (
            await NodeRow.select(NodeRow.search_only)
            .where(NodeRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return data["search_only"] if data else NodeRow.search_only.default

    async def update_search_only(self, search_only: bool) -> None:
        """Update the node's search only setting in the database"""
        await NodeRow.insert(NodeRow(id=self.id, search_only=search_only)).on_conflict(
            action="DO UPDATE", target=NodeRow.id, values=[NodeRow.search_only]
        )
        await self.update_cache((self.fetch_search_only, search_only), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_managed(self) -> bool:
        """Fetch the node's managed setting from the database.

        Returns
        -------
        bool
            The node's managed setting.
        """
        data = (
            await NodeRow.select(NodeRow.managed)
            .where(NodeRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return data["managed"] if data else NodeRow.managed.default

    async def update_managed(self, managed: bool) -> None:
        """Update the node's managed setting in the database"""
        await NodeRow.insert(NodeRow(id=self.id, managed=managed)).on_conflict(
            action="DO UPDATE", target=NodeRow.id, values=[NodeRow.managed]
        )
        await self.update_cache((self.fetch_managed, managed), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_extras(self) -> JSON_DICT_TYPE:
        """Fetch the node's extras from the database.

        Returns
        -------
        dict
            The node's extras.
        """
        data = (
            await NodeRow.select(NodeRow.extras)
            .where(NodeRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return data["extras"] if data else json.loads(NodeRow.extras.default)

    async def update_extras(self, extras: JSON_DICT_TYPE) -> None:
        """Update the node's extras in the database"""
        await NodeRow.insert(NodeRow(id=self.id, extras=extras)).on_conflict(
            action="DO UPDATE", target=NodeRow.id, values=[NodeRow.extras]
        )
        await self.update_cache((self.fetch_extras, extras), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_yaml(self) -> JSON_DICT_TYPE:
        """Fetch the node's yaml from the database.

        Returns
        -------
        dict
            The node's yaml.
        """
        data = (
            await NodeRow.select(NodeRow.yaml).where(NodeRow.id == self.id).first().output(load_json=True, nested=True)
        )
        return data["yaml"] if data else json.loads(NodeRow.yaml.default)

    async def update_yaml(self, yaml_data: JSON_DICT_TYPE) -> None:
        """Update the node's yaml in the database"""
        await NodeRow.insert(NodeRow(id=self.id, yaml=yaml_data)).on_conflict(
            action="DO UPDATE", target=NodeRow.id, values=[NodeRow.yaml]
        )
        await self.update_cache((self.fetch_yaml, yaml_data), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_disabled_sources(self) -> list[str]:
        """Fetch the node's disabled sources from the database.

        Returns
        -------
        list[str]
            The node's disabled sources.
        """
        data = (
            await NodeRow.select(NodeRow.disabled_sources)
            .where(NodeRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return data["disabled_sources"] if data else NodeRow.disabled_sources.default

    async def update_disabled_sources(self, disabled_sources: list[str]) -> None:
        """Update the node's disabled sources in the database"""
        source = set(map(str.strip, map(str.lower, disabled_sources)))
        intersection = list(source & SUPPORTED_SOURCES.union(SUPPORTED_FEATURES))
        await NodeRow.insert(NodeRow(id=self.id, disabled_sources=intersection)).on_conflict(
            action="DO UPDATE", target=NodeRow.id, values=[NodeRow.disabled_sources]
        )
        await self.update_cache((self.fetch_disabled_sources, intersection), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    async def add_to_disabled_sources(self, source: str) -> None:
        """Add a source to the node's disabled sources in the database"""
        await NodeRow.insert(NodeRow(id=self.id, disabled_sources=[source])).on_conflict(
            action="DO UPDATE",
            target=NodeRow.id,
            values=[
                (NodeRow.disabled_sources, QueryString("array_cat(node.disabled_sources, EXCLUDED.disabled_sources)"))
            ],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_disabled_sources)

    async def remove_from_disabled_sources(self, source: str) -> None:
        """Remove a source from the node's disabled sources in the database"""
        await NodeRow.update(disabled_sources=QueryString("array_remove(disabled_sources, {})", source)).where(
            NodeRow.id == self.id
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_disabled_sources)

    async def bulk_add_to_disabled_sources(self, sources: list[str]) -> None:
        """Add sources to the node's disabled sources in the database"""
        source = set(map(str.strip, map(str.lower, [sources])))
        intersection = list(source & SUPPORTED_SOURCES.union(SUPPORTED_FEATURES))
        await NodeRow.insert(NodeRow(id=self.id, disabled_sources=intersection)).on_conflict(
            action="DO UPDATE",
            target=NodeRow.id,
            values=[(NodeRow.disabled_sources, QueryString("node.disabled_sources || EXCLUDED.disabled_sources"))],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_disabled_sources)

    async def bulk_remove_from_disabled_sources(self, sources: list[str]) -> None:
        """Remove sources from the node's disabled sources in the database"""
        if not sources:
            return
        for source in sources:
            await self.remove_from_disabled_sources(source)

    async def bulk_update(
        self,
        host: str,
        port: int,
        password: str,
        resume_timeout: int = 60,
        name: str | None = None,
        reconnect_attempts: int = -1,
        ssl: bool = False,
        search_only: bool = False,
        managed: bool = False,
        extras: JSON_DICT_TYPE | None = None,
        yaml: JSON_DICT_TYPE | None = None,
        disabled_sources: list[str] | None = None,
    ) -> None:
        """Update the node's data in the database"""
        yaml_data = yaml or {"server": {}, "lavalink": {"server": {}}}
        yaml_data["server"]["address"] = host  # type: ignore
        yaml_data["server"]["port"] = port  # type: ignore
        yaml_data["lavalink"]["server"]["password"] = password
        if disabled_sources is None:
            disabled_sources = []
        if extras is None:
            extras = {}
        await NodeRow.insert(
            NodeRow(
                id=self.id,
                name=name,
                ssl=ssl,
                resume_key=None,
                resume_timeout=resume_timeout,
                reconnect_attempts=reconnect_attempts,
                search_only=search_only,
                managed=managed,
                disabled_sources=disabled_sources,
                extras=extras,
                yaml=yaml,
            )
        ).on_conflict(
            action="DO UPDATE",
            target=NodeRow.id,
            values=[
                NodeRow.name,
                NodeRow.ssl,
                NodeRow.resume_timeout,
                NodeRow.reconnect_attempts,
                NodeRow.search_only,
                NodeRow.managed,
                NodeRow.disabled_sources,
                NodeRow.extras,
                NodeRow.yaml,
            ],
        )
        await self.invalidate_cache()

    async def get_connection_args(self) -> dict[str, int | str | bool | None, list[str]]:
        """Get the connection args for the node.

        Returns
        -------
        dict
            The connection args.
        """
        data = await self.fetch_all()

        if self.id in BUNDLED_NODES_IDS_HOST_MAPPING:
            data["yaml"]["lavalink"]["server"]["password"] = self.client._user_id

        return {
            "unique_identifier": self.id,
            "host": data["yaml"]["server"]["address"],
            "port": data["yaml"]["server"]["port"],
            "password": data["yaml"]["lavalink"]["server"]["password"],
            "name": data["name"],
            "ssl": data["ssl"],
            "reconnect_attempts": data["reconnect_attempts"],
            "search_only": data["search_only"],
            "resume_timeout": data["resume_timeout"],
            "disabled_sources": data["disabled_sources"],
            "managed": data["managed"],
        }

    @classmethod
    async def create_managed(cls, identifier: int) -> None:
        """Create the player in the database"""

        __, java_xmx_default, __, __ = get_jar_ram_actual(JAVA_EXECUTABLE)
        await NodeRow.insert(
            NodeRow(
                id=identifier,
                managed=True,
                ssl=False,
                reconnect_attempts=-1,
                search_only=False,
                yaml=NODE_DEFAULT_SETTINGS,
                name="PyLavManagedNode",
                resume_key=None,
                resume_timeout=600,
                extras={"max_ram": java_xmx_default},
            )
        ).on_conflict(action="DO NOTHING")

    @maybe_cached
    async def fetch_session(self) -> str | None:
        """Fetch the node's session from the database"""
        data = (
            await Sessions.select(Sessions.id)
            .where((Sessions.node == self.id) & (Sessions.bot == self.client.bot.user.id))  # noqa: E712
            .first()
            .output(load_json=True, nested=True)
        )
        return data["id"] if data else None

    async def update_session(self, session: str | None) -> None:
        """Update the node's session in the database"""
        await Sessions.insert(Sessions(id=session, node=self.id, bot=self.client.bot.user.id)).on_conflict(
            action="DO UPDATE",
            values=[Sessions.id],
            target=(Sessions.node, Sessions.bot),
        )
        await self.update_cache((self.fetch_session, session))
