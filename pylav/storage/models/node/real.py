from __future__ import annotations

from dataclasses import dataclass

import ujson

from pylav.constants.config import JAVA_EXECUTABLE
from pylav.constants.node import NODE_DEFAULT_SETTINGS
from pylav.constants.node_features import SUPPORTED_FEATURES, SUPPORTED_SOURCES
from pylav.extension.bundled_node.utils import get_jar_ram_actual
from pylav.helpers.singleton import SingletonCachedByKey
from pylav.storage.database.cache.decodators import maybe_cached
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.nodes import NodeRow
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
            "extras": ujson.loads(NodeRow.extras.default),
            "yaml": ujson.loads(NodeRow.yaml.default),
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
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node (id, name) VALUES ({}, {})
            ON CONFLICT (id) DO UPDATE SET name = excluded.name;
            """,
            self.id,
            name,
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
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node (id, ssl) VALUES ({}, {})
            ON CONFLICT (id) DO UPDATE SET ssl = excluded.ssl;
            """,
            self.id,
            ssl,
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
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node (id, resume_timeout) VALUES ({}, {})
            ON CONFLICT (id) DO UPDATE SET resume_timeout = excluded.resume_timeout;
            """,
            self.id,
            resume_timeout,
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
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node (id, reconnect_attempts) VALUES ({}, {})
            ON CONFLICT (id) DO UPDATE SET reconnect_attempts = excluded.reconnect_attempts;
            """,
            self.id,
            reconnect_attempts,
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
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node (id, search_only) VALUES ({}, {})
            ON CONFLICT (id) DO UPDATE SET search_only = excluded.search_only;
            """,
            self.id,
            search_only,
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
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node (id, managed) VALUES ({}, {})
            ON CONFLICT (id) DO UPDATE SET managed = excluded.managed;
            """,
            self.id,
            managed,
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
        return data["extras"] if data else ujson.loads(NodeRow.extras.default)

    async def update_extras(self, extras: JSON_DICT_TYPE) -> None:
        """Update the node's extras in the database"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node (id, extras) VALUES ({}, {})
            ON CONFLICT (id) DO UPDATE SET extras = excluded.extras;
            """,
            self.id,
            ujson.dumps(extras),
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
        return data["yaml"] if data else ujson.loads(NodeRow.yaml.default)

    async def update_yaml(self, yaml_data: JSON_DICT_TYPE) -> None:
        """Update the node's yaml in the database"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node (id, yaml) VALUES ({}, {})
            ON CONFLICT (id) DO UPDATE SET yaml = excluded.yaml;
            """,
            self.id,
            ujson.dumps(yaml_data),
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
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node (id, disabled_sources) VALUES ({}, {})
            ON CONFLICT (id) DO UPDATE SET disabled_sources = excluded.disabled_sources;
            """,
            self.id,
            intersection,
        )
        await self.update_cache((self.fetch_disabled_sources, intersection), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    async def add_to_disabled_sources(self, source: str) -> None:
        """Add a source to the node's disabled sources in the database"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node (id, disabled_sources) VALUES ({}, {})
            ON CONFLICT (id)
            DO UPDATE SET disabled_sources = ARRAY_CAT(node.disabled_sources, EXCLUDED.disabled_sources);
            """,
            self.id,
            [source],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_disabled_sources)

    async def remove_from_disabled_sources(self, source: str) -> None:
        """Remove a source from the node's disabled sources in the database"""
        # TODO: When piccolo add support to more Array operations replace with ORM
        await NodeRow.raw(
            """UPDATE node SET disabled_sources = array_remove(disabled_sources, {}) WHERE id = {}""",
            source,
            self.id,
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_disabled_sources)

    async def bulk_add_to_disabled_sources(self, sources: list[str]) -> None:
        """Add sources to the node's disabled sources in the database"""
        source = set(map(str.strip, map(str.lower, [sources])))
        intersection = list(source & SUPPORTED_SOURCES.union(SUPPORTED_FEATURES))
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node (id, disabled_sources) VALUES ({}, {})
            ON CONFLICT (id) DO UPDATE SET disabled_sources = disabled_sources || EXCLUDED.disabled_sources;
            """,
            self.id,
            intersection,
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
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node
            (id,
            name,
            ssl,
            resume_key,
            resume_timeout,
            reconnect_attempts,
            search_only,
            managed,
            disabled_sources,
            extras,
            yaml)
            VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})
            ON CONFLICT (id)
            DO UPDATE
              SET name = excluded.name,
              ssl = excluded.ssl,
              resume_key = excluded.resume_key,
              resume_timeout = excluded.resume_timeout,
              reconnect_attempts = excluded.reconnect_attempts,
              search_only = excluded.search_only,
              managed = excluded.managed,
              disabled_sources = excluded.disabled_sources,
              extras = excluded.extras,
              yaml = excluded.yaml;
            """,
            self.id,
            name,
            ssl,
            None,
            resume_timeout,
            reconnect_attempts,
            search_only,
            managed,
            disabled_sources,
            ujson.dumps(extras),
            ujson.dumps(yaml_data),
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
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await NodeRow.raw(
            """
            INSERT INTO node
            (id, managed, ssl, reconnect_attempts, search_only, yaml, name, resume_key, resume_timeout, extras)
            VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {})
            ON CONFLICT (id) DO NOTHING;
            ;
            """,
            identifier,
            True,
            False,
            -1,
            False,
            ujson.dumps(NODE_DEFAULT_SETTINGS),
            "PyLavManagedNode",
            None,
            600,
            ujson.dumps({"max_ram": java_xmx_default}),
        )
