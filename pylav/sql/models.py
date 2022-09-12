from __future__ import annotations

import datetime
import gzip
import io
import pathlib
import random
import re
import sys
import typing
from collections.abc import Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import _make_key  # type: ignore

import aiohttp
import asyncstdlib
import discord
import ujson
import yaml
from discord.utils import utcnow
from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

from pylav.envvars import CACHING_ENABLED, JAVA_EXECUTABLE
from pylav.sql.caching import CachedModel, _SingletonByKey, maybe_cached
from pylav.vendored import aiopath

try:
    import brotli

    BROTLI_ENABLED = False
except ImportError:
    BROTLI_ENABLED = False

from pylav._logging import getLogger
from pylav.constants import BUNDLED_PLAYLIST_IDS, SUPPORTED_SOURCES
from pylav.exceptions import InvalidPlaylist
from pylav.filters import Equalizer
from pylav.sql import tables
from pylav.types import BotT
from pylav.utils import PyLavContext, TimedFeature, get_jar_ram_actual, get_true_path

BRACKETS: re.Pattern = re.compile(r"[\[\]]")

LOGGER = getLogger("PyLav.DBModels")


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class NodeModel(CachedModel, metaclass=_SingletonByKey):
    id: int

    @maybe_cached
    async def exists(self) -> bool:
        """Check if the node exists in the database.

        Returns
        -------
        bool
            Whether the node exists in the database.
        """
        return await tables.NodeRow.raw("SELECT EXISTS(SELECT 1 FROM node WHERE id = {});", self.id)

    async def delete(self) -> None:
        """Delete the node from the database"""
        await tables.NodeRow.raw("DELETE FROM node WHERE id = {}", self.id)
        await self.invalidate_cache()

    @maybe_cached
    async def fetch_all(self) -> dict:
        response = await tables.NodeRow.raw(
            """
        SELECT *
        FROM node
        WHERE id = {}
        LIMIT 1
        """,
            self.id,
        )
        if response:
            data = response[0]
            data["extras"] = ujson.loads(data["extras"])
            data["yaml"] = ujson.loads(data["yaml"])
            return data
        return {
            "id": self.id,
            "name": tables.NodeRow.name.default,
            "ssl": tables.NodeRow.ssl.default,
            "resume_key": tables.NodeRow.resume_key.default,
            "resume_timeout": tables.NodeRow.resume_timeout.default,
            "reconnect_attempts": tables.NodeRow.reconnect_attempts.default,
            "search_only": tables.NodeRow.search_only.default,
            "managed": tables.NodeRow.managed.default,
            "extras": ujson.loads(tables.NodeRow.extras.default),
            "yaml": ujson.loads(tables.NodeRow.yaml.default),
            "disabled_sources": tables.NodeRow.disabled_sources.default,
        }

    @maybe_cached
    async def fetch_name(self) -> str:
        """Fetch the node from the database.

        Returns
        -------
        ste
            The node's name.
        """
        data = await tables.NodeRow.raw("SELECT name FROM node WHERE id = {} LIMIT 1", self.id)
        return data[0]["name"] if data else None

    async def update_name(self, name: str) -> None:
        """Update the node's name in the database"""
        await tables.NodeRow.raw(
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
        data = await tables.NodeRow.raw("SELECT ssl FROM node WHERE id = {} LIMIT 1", self.id)
        return data[0]["ssl"] if data else tables.NodeRow.ssl.default

    async def update_ssl(self, ssl: bool) -> None:
        """Update the node's ssl setting in the database"""
        await tables.NodeRow.raw(
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
    async def fetch_resume_key(self) -> str | None:
        """Fetch the node's resume key from the database.

        Returns
        -------
        str
            The node's resume key.
        """
        data = await tables.NodeRow.raw("SELECT resume_key FROM node WHERE id = {} LIMIT 1", self.id)
        return data[0]["resume_key"] if data else None

    async def update_resume_key(self, resume_key: str) -> None:
        """Update the node's resume key in the database"""
        await tables.NodeRow.raw(
            """
            INSERT INTO
                node (id, resume_key)
            VALUES
                ({}, {})
            ON CONFLICT (id) DO UPDATE SET resume_key = excluded.resume_key;
            """,
            self.id,
            resume_key,
        )
        await self.update_cache((self.fetch_resume_key, resume_key), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_resume_timeout(self) -> int:
        """Fetch the node's resume timeout from the database.

        Returns
        -------
        int
            The node's resume timeout.
        """
        data = await tables.NodeRow.raw("SELECT resume_timeout FROM node WHERE id = {} LIMIT 1", self.id)
        return data[0]["resume_timeout"] if data else tables.NodeRow.resume_timeout.default

    async def update_resume_timeout(self, resume_timeout: int) -> None:
        """Update the node's resume timeout in the database"""
        await tables.NodeRow.raw(
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
        data = await tables.NodeRow.raw("SELECT reconnect_attempts FROM node WHERE id = {} LIMIT 1", self.id)
        return data[0]["reconnect_attempts"] if data else tables.NodeRow.reconnect_attempts.default

    async def update_reconnect_attempts(self, reconnect_attempts: int) -> None:
        """Update the node's reconnect attempts in the database"""
        await tables.NodeRow.raw(
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
        data = await tables.NodeRow.raw("SELECT search_only FROM node WHERE id = {} LIMIT 1", self.id)
        return data[0]["search_only"] if data else tables.NodeRow.search_only.default

    async def update_search_only(self, search_only: bool) -> None:
        """Update the node's search only setting in the database"""
        await tables.NodeRow.raw(
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
        data = await tables.NodeRow.raw("SELECT managed FROM node WHERE id = {} LIMIT 1", self.id)
        return data[0]["managed"] if data else tables.NodeRow.managed.default

    async def update_managed(self, managed: bool) -> None:
        """Update the node's managed setting in the database"""
        await tables.NodeRow.raw(
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
    async def fetch_extras(self) -> dict:
        """Fetch the node's extras from the database.

        Returns
        -------
        dict
            The node's extras.
        """
        data = await tables.NodeRow.raw("SELECT extras FROM node WHERE id = {} LIMIT 1", self.id)
        return ujson.loads(data[0]["extras"] if data else tables.NodeRow.extras.default)

    async def update_extras(self, extras: dict) -> None:
        """Update the node's extras in the database"""
        await tables.NodeRow.raw(
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
    async def fetch_yaml(self) -> dict:
        """Fetch the node's yaml from the database.

        Returns
        -------
        dict
            The node's yaml.
        """
        data = await tables.NodeRow.raw("SELECT yaml FROM node WHERE id = {} LIMIT 1", self.id)
        if data:
            return ujson.loads(data[0]["yaml" if data[0]["yaml"] != "{}" else tables.NodeRow.yaml.default])
        return {}

    async def update_yaml(self, yaml_data: dict) -> None:
        """Update the node's yaml in the database"""
        await tables.NodeRow.raw(
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
        data = await tables.NodeRow.raw("SELECT disabled_sources FROM node WHERE id = {} LIMIT 1", self.id)
        return data[0]["disabled_sources"] if data else tables.NodeRow.disabled_sources.default

    async def update_disabled_sources(self, disabled_sources: list[str]) -> None:
        """Update the node's disabled sources in the database"""
        source = set(map(str.strip, map(str.lower, disabled_sources)))
        intersection = list(source & SUPPORTED_SOURCES)
        await tables.NodeRow.raw(
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
        await tables.NodeRow.raw(
            """
            INSERT INTO node (id, disabled_sources) VALUES ({}, {})
            ON CONFLICT (id) DO UPDATE SET disabled_sources = ARRAY_CAT(node.disabled_sources, EXCLUDED.disabled_sources);
            """,
            self.id,
            [source],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_disabled_sources)

    async def remove_from_disabled_sources(self, source: str) -> None:
        """Remove a source from the node's disabled sources in the database"""
        await tables.NodeRow.raw(
            """UPDATE node SET disabled_sources = array_remove(disabled_sources, {}) WHERE id = {}""",
            source,
            self.id,
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_disabled_sources)

    async def bulk_add_to_disabled_sources(self, sources: list[str]) -> None:
        """Add sources to the node's disabled sources in the database"""
        source = set(map(str.strip, map(str.lower, [sources])))
        intersection = list(source & SUPPORTED_SOURCES)
        await tables.NodeRow.raw(
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
        resume_key: str = None,
        resume_timeout: int = 60,
        name: str = None,
        reconnect_attempts: int = -1,
        ssl: bool = False,
        search_only: bool = False,
        managed: bool = False,
        extras: dict = None,
        yaml: dict = None,
        disabled_sources: list[str] = None,
    ) -> None:
        """Update the node's data in the database"""
        yaml = yaml or {"server": {}, "lavalink": {"server": {}}}
        yaml["server"]["address"] = host  # type: ignore
        yaml["server"]["port"] = port  # type: ignore
        yaml["lavalink"]["server"]["password"] = password
        if disabled_sources is None:
            disabled_sources = []
        if extras is None:
            extras = {}
        await tables.NodeRow.raw(
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
            resume_key,
            resume_timeout,
            reconnect_attempts,
            search_only,
            managed,
            disabled_sources,
            ujson.dumps(extras),
            ujson.dumps(yaml),
        )
        await self.invalidate_cache()

    async def get_connection_args(self) -> dict:
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
            "resume_key": data["resume_key"],
            "disabled_sources": data["disabled_sources"],
            "managed": data["managed"],
        }

    @classmethod
    async def create_managed(cls, id: int) -> None:
        """Create the player in the database"""
        from pylav.utils.built_in_node import NODE_DEFAULT_SETTINGS

        __, java_xmx_default, __, __ = get_jar_ram_actual(JAVA_EXECUTABLE)

        await tables.NodeRow.raw(
            """
                    INSERT INTO node
                    (id, managed, ssl, reconnect_attempts, search_only, yaml, name, resume_key, resume_timeout, extras)
                    VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {})
                    ON CONFLICT (id) DO NOTHING;
                    ;
                    """,
            id,
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


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class NodeModelMock(metaclass=_SingletonByKey):
    id: int
    data: dict

    @staticmethod
    async def exists() -> bool:
        """Check if the node exists in the database.

        Returns
        -------
        bool
            Whether the node exists in the database.
        """
        return False

    async def delete(self) -> None:
        """Delete the node from the database"""

    async def fetch_all(self) -> dict:
        return {"id": self.id, **self.data}

    async def fetch_name(self) -> str:
        """Fetch the node from the database.

        Returns
        -------
        ste
            The node's name.
        """
        return self.data["name"]

    async def update_name(self, name: str) -> None:
        """Update the node's name in the database"""
        self.data["name"] = name

    async def fetch_ssl(self) -> bool:
        """Fetch the node's ssl setting from the database.

        Returns
        -------
        bool
            The node's ssl setting.
        """
        return self.data["ssl"]

    async def update_ssl(self, ssl: bool) -> None:
        """Update the node's ssl setting in the database"""
        self.data["ssl"] = ssl

    async def fetch_resume_key(self) -> str | None:
        """Fetch the node's resume key from the database.

        Returns
        -------
        str
            The node's resume key.
        """
        return self.data["resume_key"]

    async def update_resume_key(self, resume_key: str) -> None:
        """Update the node's resume key in the database"""

    async def fetch_resume_timeout(self) -> int:
        """Fetch the node's resume timeout from the database.

        Returns
        -------
        int
            The node's resume timeout.
        """
        return self.data["resume_timeout"]

    async def update_resume_timeout(self, resume_timeout: int) -> None:
        """Update the node's resume timeout in the database"""
        self.data["resume_timeout"] = resume_timeout

    async def fetch_reconnect_attempts(self) -> int:
        """Fetch the node's reconnect attempts from the database.

        Returns
        -------
        int
            The node's reconnect attempts.
        """
        return self.data["reconnect_attempts"]

    async def update_reconnect_attempts(self, reconnect_attempts: int) -> None:
        """Update the node's reconnect attempts in the database"""
        self.data["reconnect_attempts"] = reconnect_attempts

    async def fetch_search_only(self) -> bool:
        """Fetch the node's search only setting from the database.

        Returns
        -------
        bool
            The node's search only setting.
        """
        return self.data["search_only"]

    async def update_search_only(self, search_only: bool) -> None:
        """Update the node's search only setting in the database"""
        self.data["search_only"] = search_only

    async def fetch_managed(self) -> bool:
        """Fetch the node's managed setting from the database.

        Returns
        -------
        bool
            The node's managed setting.
        """
        return self.data["managed"]

    async def update_managed(self, managed: bool) -> None:
        """Update the node's managed setting in the database"""
        self.data["managed"] = managed

    async def fetch_extras(self) -> dict:
        """Fetch the node's extras from the database.

        Returns
        -------
        dict
            The node's extras.
        """
        return self.data["extras"]

    async def update_extras(self, extras: dict) -> None:
        """Update the node's extras in the database"""
        self.data["extras"] = extras

    async def fetch_yaml(self) -> dict:
        """Fetch the node's yaml from the database.

        Returns
        -------
        dict
            The node's yaml.
        """
        return self.data["yaml"]

    async def update_yaml(self, yaml_data: dict) -> None:
        """Update the node's yaml in the database"""
        self.data["yaml"] = yaml_data

    async def fetch_disabled_sources(self) -> list[str]:
        """Fetch the node's disabled sources from the database.

        Returns
        -------
        list[str]
            The node's disabled sources.
        """
        return self.data["disabled_sources"]

    async def update_disabled_sources(self, disabled_sources: list[str]) -> None:
        """Update the node's disabled sources in the database"""
        source = set(map(str.strip, map(str.lower, disabled_sources)))
        intersection = list(source & SUPPORTED_SOURCES)
        self.data["disabled_sources"] = intersection

    async def add_to_disabled_sources(self, source: str) -> None:
        """Add a source to the node's disabled sources in the database"""
        data = set(self.data["disabled_sources"])
        data.update([source])
        self.data["disabled_sources"] = list(data)

    async def remove_from_disabled_sources(self, source: str) -> None:
        """Remove a source from the node's disabled sources in the database"""
        data = set(self.data["disabled_sources"])
        data.discard(source)
        self.data["disabled_sources"] = list(data)

    async def bulk_add_to_disabled_sources(self, sources: list[str]) -> None:
        """Add sources to the node's disabled sources in the database"""
        source = set(map(str.strip, map(str.lower, [sources])))
        source.update(self.data["disabled_sources"])
        intersection = list(source & SUPPORTED_SOURCES)
        self.data["disabled_sources"] = intersection

    async def bulk_remove_from_disabled_sources(self, sources: list[str]) -> None:
        """Remove sources from the node's disabled sources in the database"""
        if not sources:
            return
        for source in sources:
            await self.remove_from_disabled_sources(source)

    async def get_connection_args(self) -> dict:
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
            "resume_key": data["resume_key"],
            "disabled_sources": data["disabled_sources"],
            "managed": data["managed"],
            "temporary": True,
        }

    @classmethod
    async def create_managed(cls, id: int) -> None:
        """Create the player in the database"""


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class PlayerModel(CachedModel, metaclass=_SingletonByKey):
    id: int
    bot: int

    @classmethod
    async def create_global(cls, bot: int) -> None:
        """Create the player in the database"""
        data = ujson.dumps(
            {
                "enabled": False,
                "time": 60,
            }
        )
        await tables.PlayerRow.raw(
            """
                INSERT INTO player
                (id, bot, volume, max_volume, shuffle, auto_shuffle, auto_play, self_deaf, empty_queue_dc, alone_dc, alone_pause)
                VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})
                ON CONFLICT (id, bot) DO NOTHING;
                ;
                """,
            0,
            bot,
            1000,
            1000,
            True,
            True,
            True,
            True,
            data,
            data,
            data,
        )

    async def delete(self) -> None:
        """Delete the player from the database"""
        await tables.PlayerRow.raw("DELETE FROM player WHERE id = {} and bot = {};", self.id, self.bot)
        await self.invalidate_cache()

    @maybe_cached
    async def fetch_all(self) -> dict:
        """Get all players from the database"""
        response = await tables.PlayerRow.raw(
            """SELECT * FROM player WHERE id = {} AND bot = {} LIMIT 1;""",
            self.id,
            self.bot,
        )
        if response:
            data = response[0]
            del data["primary_key"]
            data["empty_queue_dc"] = TimedFeature.from_json(ujson.loads(data["empty_queue_dc"]))
            data["alone_dc"] = TimedFeature.from_json(ujson.loads(data["alone_dc"]))
            data["alone_pause"] = TimedFeature.from_json(ujson.loads(data["alone_pause"]))
            data["extras"] = ujson.loads(data["extras"])
            data["effects"] = ujson.loads(data["effects"])
            return data
        return {
            "id": self.id,
            "bot": self.bot,
            "volume": tables.PlayerRow.volume.default,
            "max_volume": tables.PlayerRow.max_volume.default,
            "auto_play_playlist_id": tables.PlayerRow.auto_play_playlist_id.default,
            "text_channel_id": tables.PlayerRow.text_channel_id.default,
            "notify_channel_id": tables.PlayerRow.notify_channel_id.default,
            "forced_channel_id": tables.PlayerRow.forced_channel_id.default,
            "repeat_current": tables.PlayerRow.repeat_current.default,
            "repeat_queue": tables.PlayerRow.repeat_queue.default,
            "shuffle": tables.PlayerRow.shuffle.default,
            "auto_shuffle": tables.PlayerRow.auto_shuffle.default,
            "auto_play": tables.PlayerRow.auto_play.default,
            "self_deaf": tables.PlayerRow.self_deaf.default,
            "empty_queue_dc": TimedFeature.from_json(ujson.loads(tables.PlayerRow.empty_queue_dc.default)),
            "alone_dc": TimedFeature.from_json(ujson.loads(tables.PlayerRow.alone_dc.default)),
            "alone_pause": TimedFeature.from_json(ujson.loads(tables.PlayerRow.alone_pause.default)),
            "extras": ujson.loads(tables.PlayerRow.extras.default),
            "effects": ujson.loads(tables.PlayerRow.effects.default),
            "dj_users": tables.PlayerRow.dj_users.default,
            "dj_roles": tables.PlayerRow.dj_roles.default,
        }

    @maybe_cached
    async def exists(self) -> bool:
        """Check if the player exists in the database"""
        return await tables.PlayerRow.raw(
            "SELECT EXISTS(SELECT 1 FROM player WHERE id = {} and bot = {});", self.id, self.bot
        )

    @maybe_cached
    async def fetch_volume(self) -> int:
        """Fetch the volume of the player from the db"""
        player = await tables.PlayerRow.raw(
            """SELECT volume FROM player WHERE id = {} AND bot = {} LIMIT 1""", self.id, self.bot
        )
        return player[0]["volume"] if player else tables.PlayerRow.volume.default

    async def update_volume(self, volume: int) -> None:
        """Update the volume of the player in the db"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, volume)
        VALUES ({}, {}, {})
        ON CONFLICT (id, bot)
         DO UPDATE SET volume = excluded.volume;""",
            self.id,
            self.bot,
            volume,
        )
        await self.update_cache((self.fetch_volume, volume), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_max_volume(self) -> int:
        """Fetch the max volume of the player from the db"""
        player = await tables.PlayerRow.raw(
            """SELECT max_volume FROM player WHERE id = {} AND bot = {} LIMIT 1""", self.id, self.bot
        )
        return player[0]["max_volume"] if player else tables.PlayerRow.max_volume.default

    async def update_max_volume(self, max_volume: int) -> None:
        """Update the max volume of the player in the db"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, max_volume)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET max_volume = excluded.max_volume;""",
            self.id,
            self.bot,
            max_volume,
        )
        await self.update_cache((self.fetch_max_volume, max_volume), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_auto_play_playlist_id(self) -> int:
        """Fetch the auto play playlist ID of the player"""
        player = await tables.PlayerRow.raw(
            """SELECT auto_play_playlist_id FROM player WHERE id = {} AND bot = {} LIMIT 1""", self.id, self.bot
        )
        return player[0]["auto_play_playlist_id"] if player else tables.PlayerRow.auto_play_playlist_id.default

    async def update_auto_play_playlist_id(self, auto_play_playlist_id: int) -> None:
        """Update the auto play playlist ID of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, auto_play_playlist_id)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET auto_play_playlist_id = excluded.auto_play_playlist_id;""",
            self.id,
            self.bot,
            auto_play_playlist_id,
        )
        await self.update_cache((self.fetch_auto_play_playlist_id, auto_play_playlist_id), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_text_channel_id(self) -> int:
        """Fetch the text channel ID of the player"""
        player = await tables.PlayerRow.raw(
            """SELECT text_channel_id FROM player WHERE id = {} AND bot = {} LIMIT 1""", self.id, self.bot
        )
        return player[0]["text_channel_id"] if player else tables.PlayerRow.text_channel_id.default

    async def update_text_channel_id(self, text_channel_id: int) -> None:
        """Update the text channel ID of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, text_channel_id)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET text_channel_id = excluded.text_channel_id;""",
            self.id,
            self.bot,
            text_channel_id,
        )
        await self.update_cache((self.fetch_text_channel_id, text_channel_id), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_notify_channel_id(self) -> int:
        """Fetch the notify channel ID of the player"""
        player = await tables.PlayerRow.raw(
            """SELECT notify_channel_id FROM player WHERE id = {} AND bot = {} LIMIT 1""", self.id, self.bot
        )

        return player[0]["notify_channel_id"] if player else tables.PlayerRow.notify_channel_id.default

    async def update_notify_channel_id(self, notify_channel_id: int) -> None:
        """Update the notify channel ID of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, notify_channel_id)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET notify_channel_id = excluded.notify_channel_id;""",
            self.id,
            self.bot,
            notify_channel_id,
        )
        await self.update_cache((self.fetch_notify_channel_id, notify_channel_id), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_forced_channel_id(self) -> int:
        """Fetch the forced channel ID of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT forced_channel_id FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return player[0]["forced_channel_id"] if player else tables.PlayerRow.forced_channel_id.default

    async def update_forced_channel_id(self, forced_channel_id: int) -> None:
        """Update the forced channel ID of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, forced_channel_id)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET forced_channel_id = excluded.forced_channel_id;""",
            self.id,
            self.bot,
            forced_channel_id,
        )
        await self.update_cache((self.fetch_forced_channel_id, forced_channel_id), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_repeat_current(self) -> bool:
        """Fetch the repeat current of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT repeat_current FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return player[0]["repeat_current"] if player else tables.PlayerRow.repeat_current.default

    async def update_repeat_current(self, repeat_current: bool) -> None:
        """Update the repeat current of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, repeat_current)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET repeat_current = excluded.repeat_current;""",
            self.id,
            self.bot,
            repeat_current,
        )
        await self.update_cache((self.fetch_repeat_current, repeat_current), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_repeat_queue(self) -> bool:
        """Fetch the repeat queue of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT repeat_queue FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return player[0]["repeat_queue"] if player else tables.PlayerRow.repeat_queue.default

    async def update_repeat_queue(self, repeat_queue: bool) -> None:
        """Update the repeat queue of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, repeat_queue)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET repeat_queue = excluded.repeat_queue;""",
            self.id,
            self.bot,
            repeat_queue,
        )
        await self.update_cache((self.fetch_repeat_queue, repeat_queue), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_shuffle(self) -> bool:
        """Fetch the shuffle of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT shuffle FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return player[0]["shuffle"] if player else tables.PlayerRow.shuffle.default

    async def update_shuffle(self, shuffle: bool) -> None:
        """Update the shuffle of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, shuffle)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET shuffle = excluded.shuffle;""",
            self.id,
            self.bot,
            shuffle,
        )
        await self.update_cache((self.fetch_shuffle, shuffle), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_auto_shuffle(self) -> bool:
        """Fetch the auto shuffle of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT auto_shuffle FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return player[0]["auto_shuffle"] if player else tables.PlayerRow.auto_shuffle.default

    async def update_auto_shuffle(self, auto_shuffle: bool) -> None:
        """Update the auto shuffle of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, auto_shuffle)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET auto_shuffle = excluded.auto_shuffle;""",
            self.id,
            self.bot,
            auto_shuffle,
        )
        await self.update_cache((self.fetch_auto_shuffle, auto_shuffle), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_auto_play(self) -> bool:
        """Fetch the auto play of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT auto_play FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return player[0]["auto_play"] if player else tables.PlayerRow.auto_play.default

    async def update_auto_play(self, auto_play: bool) -> None:
        """Update the auto play of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, auto_play)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET auto_play = excluded.auto_play;""",
            self.id,
            self.bot,
            auto_play,
        )
        await self.update_cache((self.fetch_auto_play, auto_play), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_self_deaf(self) -> bool:
        """Fetch the self deaf of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT self_deaf FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return player[0]["self_deaf"] if player else tables.PlayerRow.self_deaf.default

    async def update_self_deaf(self, self_deaf: bool) -> None:
        """Update the self deaf of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, self_deaf)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET self_deaf = excluded.self_deaf;""",
            self.id,
            self.bot,
            self_deaf,
        )
        await self.update_cache((self.fetch_self_deaf, self_deaf), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_extras(self) -> dict:
        """Fetch the extras of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT extras FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return ujson.loads(player[0]["extras"] if player else tables.PlayerRow.extras.default)

    async def update_extras(self, extras: dict) -> None:
        """Update the extras of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, extras)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET extras = excluded.extras;""",
            self.id,
            self.bot,
            ujson.dumps(extras),
        )
        await self.update_cache((self.fetch_extras, extras), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_effects(self) -> dict:
        """Fetch the effects of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT effects FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return ujson.loads(player[0]["effects"] if player else tables.PlayerRow.effects.default)

    async def update_effects(self, effects: dict) -> None:
        """Update the effects of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, effects)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET effects = excluded.effects;""",
            self.id,
            self.bot,
            ujson.dumps(effects),
        )
        await self.update_cache((self.fetch_effects, effects), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_empty_queue_dc(self) -> TimedFeature:
        """Fetch the empty queue dc of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT empty_queue_dc FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return TimedFeature.from_json(
            ujson.loads(player[0]["empty_queue_dc"] if player else tables.PlayerRow.empty_queue_dc.default)
        )

    async def update_empty_queue_dc(self, empty_queue_dc: dict) -> None:
        """Update the empty queue dc of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, empty_queue_dc)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET empty_queue_dc = excluded.empty_queue_dc;""",
            self.id,
            self.bot,
            ujson.dumps(empty_queue_dc),
        )
        await self.update_cache((self.fetch_empty_queue_dc, empty_queue_dc), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_alone_dc(self) -> TimedFeature:
        """Fetch the alone dc of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT alone_dc FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return TimedFeature.from_json(
            ujson.loads(player[0]["alone_dc"] if player else tables.PlayerRow.alone_dc.default)
        )

    async def update_alone_dc(self, alone_dc: dict) -> None:
        """Update the alone dc of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, alone_dc)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET alone_dc = excluded.alone_dc;""",
            self.id,
            self.bot,
            ujson.dumps(alone_dc),
        )
        await self.update_cache((self.fetch_alone_dc, alone_dc), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_alone_pause(self) -> TimedFeature:
        """Fetch the alone pause of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT alone_pause FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )
        return TimedFeature.from_json(
            ujson.loads(player[0]["alone_pause"] if player else tables.PlayerRow.alone_pause.default)
        )

    async def update_alone_pause(self, alone_pause: dict) -> None:
        """Update the alone pause of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, alone_pause)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET alone_pause = excluded.alone_pause;""",
            self.id,
            self.bot,
            ujson.dumps(alone_pause),
        )
        await self.update_cache((self.fetch_alone_pause, alone_pause), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_dj_users(self) -> set[int]:
        """Fetch the dj users of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT dj_users FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )

        return set(player[0]["dj_users"] if player else tables.PlayerRow.dj_users.default)

    async def add_to_dj_users(self, user: discord.Member) -> None:
        """Add a user to the dj users of the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, dj_users)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET dj_users = array_cat(player.dj_users, EXCLUDED.dj_users);""",
            self.id,
            self.bot,
            [user.id],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_users)

    async def remove_from_dj_users(self, user: discord.Member) -> None:
        """Remove a user from the dj users of the player"""
        await tables.PlayerRow.raw(
            "UPDATE player SET dj_users = array_remove(dj_users, {}) WHERE id = {} AND bot = {};",
            user.id,
            self.id,
            self.bot,
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_users)

    async def bulk_add_dj_users(self, *users: discord.Member) -> None:
        """Add dj users to the player"""
        if not users:
            return
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, dj_users)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET dj_users = array_cat(player.dj_users, EXCLUDED.dj_users);""",
            self.id,
            self.bot,
            [u.id for u in users],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_users)

    async def bulk_remove_dj_users(self, *users: discord.Member) -> None:
        """Remove dj users from the player.

        Parameters
        ----------
        users : discord.Member
            The users to add
        """
        if not users:
            return
        async with tables.DB.transaction():
            for user in users:
                await self.remove_from_dj_users(user)

    async def dj_users_reset(self) -> None:
        """Reset the dj users of the player"""
        await tables.PlayerRow.raw(
            """
            INSERT INTO player (id, bot, dj_users) VALUES ({}, {}, {})
            ON CONFLICT (id, bot) DO UPDATE SET dj_users = excluded.dj_users;
            """,
            self.id,
            self.bot,
            [],
        )
        await self.update_cache((self.fetch_dj_users, set()), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_dj_roles(self) -> set[int]:
        """Fetch the dj roles of the player"""
        player = await tables.PlayerRow.raw(
            "SELECT dj_roles FROM player WHERE id = {} AND bot = {} LIMIT 1;", self.id, self.bot
        )

        return set(player[0]["dj_roles"] if player else tables.PlayerRow.dj_roles.default)

    async def add_to_dj_roles(self, role: discord.Role) -> None:
        """Add dj roles to the player"""
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, dj_roles)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET dj_roles = array_cat(player.dj_roles, EXCLUDED.dj_roles)""",
            self.id,
            self.bot,
            [role.id],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_roles)

    async def remove_from_dj_roles(self, role: discord.Role) -> None:
        """Remove dj roles from the player"""
        await tables.PlayerRow.raw(
            """UPDATE player SET dj_roles = array_remove(dj_roles, {}) WHERE id = {} AND bot = {}""",
            role.id,
            self.id,
            self.bot,
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_roles)

    async def bulk_add_dj_roles(self, *roles: discord.Role) -> None:
        """Add dj roles to the player.

        Parameters
        ----------
        roles : discord.Role
            The roles to add"
        """
        if not roles:
            return
        await tables.PlayerRow.raw(
            """INSERT INTO player (id, bot, dj_roles)
                    VALUES ({}, {}, {})
                    ON CONFLICT (id, bot)
                    DO UPDATE SET dj_roles = array_cat(player.dj_roles, EXCLUDED.dj_roles);""",
            self.id,
            self.bot,
            [r.id for r in roles],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_roles)

    async def bulk_remove_dj_roles(self, *roles: discord.Role) -> None:
        """Remove dj roles from the player.

        Parameters
        ----------
        roles : discord.Role
            The roles to add.
        """
        if not roles:
            return
        async with tables.DB.transaction():
            for role in roles:
                await self.remove_from_dj_roles(role)

    async def dj_roles_reset(self) -> None:
        """Reset the dj roles of the player"""
        await tables.PlayerRow.raw(
            """
                    INSERT INTO player (id, bot, dj_roles) VALUES ({}, {}, {})
                    ON CONFLICT (id, bot) DO UPDATE SET dj_roles = excluded.dj_roles;
                    """,
            self.id,
            self.bot,
            [],
        )
        await self.update_cache((self.fetch_dj_roles, set()), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

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
            if hasattr(bot, "is_owner") and await bot.is_owner(typing.cast(discord.User, user)):
                return True
            if hasattr(bot, "is_admin") and await bot.is_admin(user):
                return True
            if hasattr(bot, "is_mod") and await bot.is_mod(user):
                return True
        dj_users = await self.fetch_dj_users()
        if user.id in dj_users:
            return True
        dj_roles = await self.fetch_dj_roles()
        if await asyncstdlib.any(r.id in dj_roles for r in user.roles):
            return True
        return not dj_users and not dj_roles


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class BotVersion(CachedModel, metaclass=_SingletonByKey):
    id: int

    @maybe_cached
    async def fetch_version(self) -> LegacyVersion | Version:
        """Fetch the version of the bot from the database"""
        version = await tables.BotVersionRow.raw(
            """
            SELECT version FROM version
            WHERE bot = {}
            LIMIT 1
            """,
            self.id,
        )
        return parse_version(version[0]["version"] if version else tables.BotVersionRow.version.default)

    async def update_version(self, version: LegacyVersion | Version | str):
        """Update the version of the bot in the database"""
        await tables.BotVersionRow.raw(
            """
            INSERT INTO version (bot, version)
            VALUES ({}, {})
            ON CONFLICT (bot)
            DO UPDATE SET version = EXCLUDED.version
            """,
            self.id,
            str(version),
        )
        await self.invalidate_cache(self.fetch_version)


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class LibConfigModel(CachedModel, metaclass=_SingletonByKey):
    bot: int
    id: int = 1

    @maybe_cached
    async def exists(self) -> bool:
        """Check if the config exists.

        Returns
        -------
        bool
            Whether the config exists.
        """
        return await tables.PlayerRow.raw(
            "SELECT EXISTS(SELECT 1 FROM lib_config WHERE id = {} and bot = {});", self.id, self.bot
        )

    @maybe_cached
    async def fetch_config_folder(self) -> str:
        """Fetch the config folder.

        Returns
        -------
        str
            The config folder.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT config_folder FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return response[0]["config_folder"] if response else tables.LibConfigRow.config_folder.default

    async def update_config_folder(self, config_folder: aiopath.AsyncPath | pathlib.Path | str) -> None:
        """Update the config folder.

        Parameters
        ----------
        config_folder
            The new config folder.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, config_folder)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET config_folder = EXCLUDED.config_folder
            """,
            self.id,
            self.bot,
            str(config_folder),
        )
        await self.update_cache((self.fetch_config_folder, str(config_folder)), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_localtrack_folder(self) -> str:
        """Fetch the localtrack folder.

        Returns
        -------
        str
            The localtrack folder.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT localtrack_folder FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return response[0]["localtrack_folder"] if response else tables.LibConfigRow.localtrack_folder.default

    async def update_localtrack_folder(self, localtrack_folder: aiopath.AsyncPath | pathlib.Path | str) -> None:
        """Update the localtrack folder.

        Parameters
        ----------
        localtrack_folder
            The new localtrack folder.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, localtrack_folder)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET localtrack_folder = EXCLUDED.localtrack_folder
            """,
            self.id,
            self.bot,
            str(localtrack_folder),
        )
        await self.update_cache((self.fetch_localtrack_folder, str(localtrack_folder)), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_java_path(self) -> str:
        """Fetch the java path.

        Returns
        -------
        str
            The java path.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT java_path FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        temp_path = response[0]["java_path"] if response else tables.LibConfigRow.java_path.default
        java_path = get_true_path(temp_path, temp_path)
        return java_path

    async def update_java_path(self, java_path: aiopath.AsyncPath | pathlib.Path | str) -> None:
        """Update the java path.

        Parameters
        ----------
        java_path
            The new java path.
        """
        java_path = get_true_path(java_path, java_path)
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, java_path)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET java_path = EXCLUDED.java_path
            """,
            self.id,
            self.bot,
            str(java_path),
        )
        await self.update_cache((self.fetch_java_path, str(java_path)), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_enable_managed_node(self) -> bool:
        """Fetch the enable_managed_node.

        Returns
        -------
        bool
            The enable_managed_node.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT enable_managed_node FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return response[0]["enable_managed_node"] if response else tables.LibConfigRow.enable_managed_node.default

    async def update_enable_managed_node(self, enable_managed_node: bool) -> None:
        """Update the enable_managed_node.

        Parameters
        ----------
        enable_managed_node
            The new enable_managed_node.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, enable_managed_node)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET enable_managed_node = EXCLUDED.enable_managed_node
            """,
            self.id,
            self.bot,
            enable_managed_node,
        )
        await self.update_cache((self.fetch_enable_managed_node, enable_managed_node), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_use_bundled_pylav_external(self) -> bool:
        """Fetch the use_bundled_pylav_external.

        Returns
        -------
        bool
            The use_bundled_pylav_external.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT use_bundled_pylav_external FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return (
            response[0]["use_bundled_pylav_external"]
            if response
            else tables.LibConfigRow.use_bundled_pylav_external.default
        )

    async def update_use_bundled_pylav_external(self, use_bundled_pylav_external: bool) -> None:
        """Update the use_bundled_pylav_external.

        Parameters
        ----------
        use_bundled_pylav_external
            The new use_bundled_pylav_external.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, use_bundled_pylav_external)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET use_bundled_pylav_external = EXCLUDED.use_bundled_pylav_external
            """,
            self.id,
            self.bot,
            use_bundled_pylav_external,
        )
        await self.update_cache(
            (self.fetch_use_bundled_pylav_external, use_bundled_pylav_external), (self.exists, True)
        )
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_use_bundled_lava_link_external(self) -> bool:
        """Fetch the use_bundled_lava_link_external.

        Returns
        -------
        bool
            The use_bundled_lava_link_external.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT use_bundled_lava_link_external FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return (
            response[0]["use_bundled_lava_link_external"]
            if response
            else tables.LibConfigRow.use_bundled_lava_link_external.default
        )

    async def update_use_bundled_lava_link_external(self, use_bundled_lava_link_external: bool) -> None:
        """Update the use_bundled_lava_link_external.

        Parameters
        ----------
        use_bundled_lava_link_external
            The new use_bundled_lava_link_external.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, use_bundled_lava_link_external)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET use_bundled_lava_link_external = EXCLUDED.use_bundled_lava_link_external
            """,
            self.id,
            self.bot,
            use_bundled_lava_link_external,
        )
        await self.update_cache(
            (self.fetch_use_bundled_lava_link_external, use_bundled_lava_link_external), (self.exists, True)
        )
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_download_id(self) -> int:
        """Fetch the download_id.

        Returns
        -------
        str
            The download_id.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT download_id FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return response[0]["download_id"] if response else tables.LibConfigRow.download_id.default

    async def update_download_id(self, download_id: int) -> None:
        """Update the download_id.

        Parameters
        ----------
        download_id
            The new download_id.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, download_id)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET download_id = EXCLUDED.download_id
            """,
            self.id,
            self.bot,
            download_id,
        )
        await self.update_cache((self.fetch_download_id, download_id), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_extras(self) -> dict:
        """Fetch the extras.

        Returns
        -------
        dict
            The extras.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT extras FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return ujson.loads(response[0]["extras"] if response else tables.LibConfigRow.extras.default)

    async def update_extras(self, extras: dict) -> None:
        """Update the extras.

        Parameters
        ----------
        extras
            The new extras.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, extras)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET extras = EXCLUDED.extras
            """,
            self.id,
            self.bot,
            ujson.dumps(extras),
        )
        await self.update_cache((self.fetch_extras, extras), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_next_execution_update_bundled_playlists(self) -> datetime.datetime:
        """Fetch the next_execution_update_bundled_playlists.

        Returns
        -------
        datetime.datetime
            The next_execution_update_bundled_playlists.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT next_execution_update_bundled_playlists FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return response[0]["next_execution_update_bundled_playlists"] if response else utcnow()

    async def update_next_execution_update_bundled_playlists(self, next_execution: datetime.datetime) -> None:
        """Update the next_execution_update_bundled_playlists.

        Parameters
        ----------
        next_execution
            The new next_execution_update_bundled_playlists.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, next_execution_update_bundled_playlists)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET next_execution_update_bundled_playlists = EXCLUDED.next_execution_update_bundled_playlists
            """,
            self.id,
            self.bot,
            next_execution,
        )
        await self.update_cache(
            (self.fetch_next_execution_update_bundled_playlists, next_execution), (self.exists, True)
        )
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_next_execution_update_bundled_external_playlists(self) -> datetime.datetime:
        """Fetch the next_execution_update_bundled_external_playlists.

        Returns
        -------
        datetime.datetime
            The next_execution_update_bundled_external_playlists.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT next_execution_update_bundled_external_playlists FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return response[0]["next_execution_update_bundled_external_playlists"] if response else utcnow()

    async def update_next_execution_update_bundled_external_playlists(self, next_execution: datetime.datetime) -> None:
        """Update the next_execution_update_bundled_external_playlists.

        Parameters
        ----------
        next_execution
            The new next_execution.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, next_execution_update_bundled_external_playlists)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET next_execution_update_bundled_external_playlists = EXCLUDED.next_execution_update_bundled_external_playlists
            """,
            self.id,
            self.bot,
            next_execution,
        )
        await self.update_cache(
            (self.fetch_next_execution_update_bundled_external_playlists, next_execution), (self.exists, True)
        )
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_next_execution_update_external_playlists(self) -> datetime.datetime:
        """Fetch the next_execution_update_external_playlists.

        Returns
        -------
        datetime.datetime
            The next_execution_update_external_playlists.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT next_execution_update_external_playlists FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return response[0]["next_execution_update_external_playlists"] if response else utcnow()

    async def update_next_execution_update_external_playlists(self, next_execution: datetime.datetime) -> None:
        """Update the next_execution_update_external_playlists.

        Parameters
        ----------
        next_execution
            The new next_execution.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, next_execution_update_external_playlists)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET next_execution_update_external_playlists = EXCLUDED.next_execution_update_external_playlists
            """,
            self.id,
            self.bot,
            next_execution,
        )
        await self.update_cache(
            (self.fetch_next_execution_update_external_playlists, next_execution), (self.exists, True)
        )
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_update_bot_activity(self) -> bool:
        """Fetch the update_bot_activity.

        Returns
        -------
        bool
            The update_bot_activity.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT update_bot_activity FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return response[0]["update_bot_activity"] if response else tables.LibConfigRow.update_bot_activity.default

    async def update_update_bot_activity(self, update_bot_activity: bool) -> None:
        """Update the update_bot_activity.

        Parameters
        ----------
        update_bot_activity
            The new update_bot_activity.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, update_bot_activity)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET update_bot_activity = EXCLUDED.update_bot_activity
            """,
            self.id,
            self.bot,
            update_bot_activity,
        )
        await self.update_cache((self.fetch_update_bot_activity, update_bot_activity), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_auto_update_managed_nodes(self) -> bool:
        """Fetch the auto_update_managed_nodes.

        Returns
        -------
        bool
            The auto_update_managed_nodes.
        """
        response = await tables.LibConfigRow.raw(
            """
            SELECT auto_update_managed_nodes FROM lib_config WHERE id = {} and bot = {} LIMIT 1;
            """,
            self.id,
            self.bot,
        )
        return (
            response[0]["auto_update_managed_nodes"]
            if response
            else tables.LibConfigRow.auto_update_managed_nodes.default
        )

    async def update_auto_update_managed_nodes(self, auto_update_managed_nodes: bool) -> None:
        """Update the auto_update_managed_nodes.

        Parameters
        ----------
        auto_update_managed_nodes
            The new auto_update_managed_nodes.
        """
        await tables.LibConfigRow.raw(
            """
            INSERT INTO lib_config (id, bot, auto_update_managed_nodes)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET auto_update_managed_nodes = EXCLUDED.auto_update_managed_nodes
            """,
            self.id,
            self.bot,
            auto_update_managed_nodes,
        )
        await self.update_cache((self.fetch_auto_update_managed_nodes, auto_update_managed_nodes), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    async def delete(self) -> None:
        """Delete the config from the database"""
        await tables.LibConfigRow.delete().where(
            (tables.LibConfigRow.id == self.id) & (tables.LibConfigRow.bot == self.bot)
        )
        await self.invalidate_cache()

    @maybe_cached
    async def fetch_all(self) -> dict:
        """Update all attributed for the config from the database.

        Returns
        -------
        LibConfigModel
            The updated config.
        """

        response = await tables.LibConfigRow.raw(
            """SELECT *
            FROM lib_config
            WHERE id = {} AND bot = {}
            LIMIT 1""",
            self.id,
            self.bot,
        )
        if response:
            data = response[0]
            data["extras"] = ujson.loads(data["extras"])
            data["java_path"] = get_true_path(data["java_path"], data["java_path"])
            return data
        return {
            "id": self.id,
            "bot": self.bot,
            "config_folder": tables.LibConfigRow.config_folder.default,
            "java_path": get_true_path(tables.LibConfigRow.java_path.default, tables.LibConfigRow.java_path.default),
            "enable_managed_node": tables.LibConfigRow.enable_managed_node.default,
            "auto_update_managed_nodes": tables.LibConfigRow.auto_update_managed_nodes.default,
            "localtrack_folder": tables.LibConfigRow.localtrack_folder.default,
            "download_id": tables.LibConfigRow.download_id.default,
            "update_bot_activity": tables.LibConfigRow.update_bot_activity.default,
            "use_bundled_pylav_external": tables.LibConfigRow.use_bundled_pylav_external.default,
            "use_bundled_lava_link_external": tables.LibConfigRow.use_bundled_lava_link_external.default,
            "extras": ujson.loads(tables.LibConfigRow.extras.default),
            "next_execution_update_bundled_playlists": tables.LibConfigRow.next_execution_update_bundled_playlists.default,
            "next_execution_update_bundled_external_playlists": tables.LibConfigRow.next_execution_update_bundled_external_playlists.default,
            "next_execution_update_external_playlists": tables.LibConfigRow.next_execution_update_external_playlists.default,
        }


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class PlaylistModel(CachedModel, metaclass=_SingletonByKey):
    id: int

    @maybe_cached
    async def exists(self) -> bool:
        """Check if the config exists.

        Returns
        -------
        bool
            Whether the config exists.
        """
        return await tables.PlaylistRow.raw("SELECT EXISTS(SELECT 1 FROM playlist WHERE id = {});", self.id)

    @maybe_cached
    async def fetch_all(self) -> dict:
        """Fetch all playlists from the database.

        Returns
        -------
        dict
            The playlists.
        """
        response = await tables.PlaylistRow.raw("SELECT * FROM playlist WHERE id = {} LIMIT 1", self.id)

        if response:
            data = response[0]
            data["tracks"] = ujson.loads(data["tracks"])
            return data

        return {
            "id": self.id,
            "name": tables.PlaylistRow.name.default,
            "tracks": [],
            "scope": tables.PlaylistRow.scope.default,
            "author": tables.PlaylistRow.author.default,
            "url": tables.PlaylistRow.url.default,
        }

    @maybe_cached
    async def fetch_scope(self) -> int | None:
        """Fetch the scope of the playlist.

        Returns
        -------
        int
            The scope of the playlist.
        """
        response = await tables.PlaylistRow.raw("SELECT scope FROM playlist WHERE id = {} LIMIT 1;", self.id)
        return response[0]["scope"] if response else tables.PlaylistRow.scope.default

    async def update_scope(self, scope: int):
        """Update the scope of the playlist.

        Parameters
        ----------
        scope : int
            The new scope of the playlist.
        """
        await tables.PlaylistRow.raw(
            "INSERT INTO playlist (id, scope) VALUES ({}, {}) ON CONFLICT (id) DO UPDATE SET scope = EXCLUDED.scope;",
            self.id,
            scope,
        )
        await self.update_cache((self.fetch_scope, scope), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_author(self) -> int | None:
        """Fetch the author of the playlist.

        Returns
        -------
        int
            The author of the playlist.
        """
        response = await tables.PlaylistRow.raw("SELECT author FROM playlist WHERE id = {} LIMIT 1;", self.id)
        return response[0]["author"] if response else tables.PlaylistRow.author.default

    async def update_author(self, author: int):
        """Update the author of the playlist.

        Parameters
        ----------
        author : int
            The new author of the playlist.
        """
        await tables.PlaylistRow.raw(
            "INSERT INTO playlist (id, author) VALUES ({}, {}) ON CONFLICT (id) DO UPDATE SET author = EXCLUDED.author;",
            self.id,
            author,
        )
        await self.update_cache((self.fetch_author, author), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_name(self) -> str | None:
        """Fetch the name of the playlist.

        Returns
        -------
        str
            The name of the playlist.
        """
        response = await tables.PlaylistRow.raw("SELECT name FROM playlist WHERE id = {} LIMIT 1;", self.id)
        return response[0]["name"] if response else tables.PlaylistRow.name.default

    async def update_name(self, name: str):
        """Update the name of the playlist.

        Parameters
        ----------
        name : str
            The new name of the playlist.
        """
        await tables.PlaylistRow.raw(
            "INSERT INTO playlist (id, name) VALUES ({}, {}) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;",
            self.id,
            name,
        )
        await self.update_cache((self.fetch_name, name), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_url(self) -> str | None:
        """Fetch the url of the playlist.

        Returns
        -------
        str
            The url of the playlist.
        """
        response = await tables.PlaylistRow.raw("SELECT url FROM playlist WHERE id = {} LIMIT 1;", self.id)
        return response[0]["url"] if response else tables.PlaylistRow.url.default

    async def update_url(self, url: str):
        """Update the url of the playlist.

        Parameters
        ----------
        url : str
            The new url of the playlist.
        """
        await tables.PlaylistRow.raw(
            "INSERT INTO playlist (id, url) VALUES ({}, {}) ON CONFLICT (id) DO UPDATE SET url = EXCLUDED.url;",
            self.id,
            url,
        )
        await self.update_cache((self.fetch_url, url), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_tracks(self) -> list[str]:
        """Fetch the tracks of the playlist.

        Returns
        -------
        list[str]
            The tracks of the playlist.
        """
        response = await tables.PlaylistRow.raw("SELECT tracks FROM playlist WHERE id = {} LIMIT 1;", self.id)
        return ujson.loads(response[0]["tracks"] if response else tables.PlaylistRow.tracks.default)

    async def update_tracks(self, tracks: list[str]):
        """Update the tracks of the playlist.

        Parameters
        ----------
        tracks : list[str]
            The new tracks of the playlist.
        """
        await tables.PlaylistRow.raw(
            "INSERT INTO playlist (id, tracks) VALUES ({}, {}) ON CONFLICT (id) DO UPDATE SET tracks = EXCLUDED.tracks;",
            self.id,
            ujson.dumps(tracks),
        )
        await self.update_cache(
            (self.fetch_tracks, tracks),
            (self.exists, True),
            (self.size, len(tracks)),
            (self.fetch_first, tracks[0] if tracks else None),
        )
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def size(self):
        """Count the tracks of the playlist.

        Returns
        -------
        int
            The number of tracks in the playlist.
        """
        response = await tables.PlaylistRow.raw(
            "SELECT jsonb_array_length(tracks) as size FROM playlist WHERE id = {} LIMIT 1;", self.id
        )
        return response[0]["size"] if response else 0

    async def add_track(self, tracks: list[str]):
        """Add a track to the playlist.

        Parameters
        ----------
        tracks : list[str]
            The tracks to add.
        """
        await tables.PlaylistRow.raw(
            "INSERT INTO playlist (id, tracks) VALUES ({}, {}) ON CONFLICT (id) DO UPDATE SET tracks = array_cat("
            "player.tracks, EXCLUDED.tracks);",
            self.id,
            tracks,
        )
        await self.invalidate_cache(self.fetch_tracks, self.fetch_all, self.size, self.fetch_first, self.exists)

    async def bulk_remove_tracks(self, tracks: list[str]) -> None:
        """Remove dj users from the player.

        Parameters
        ----------
        tracks : list[str]
            The track to remove
        """
        if not tracks:
            return
        async with tables.DB.transaction():
            for track in tracks:
                await self.remove_track(track)

    async def remove_track(self, track: str) -> None:
        """Remove a track from the playlist.

        Parameters
        ----------
        track : str
            The track to remove
        """
        await tables.PlaylistRow.raw(
            "UPDATE player SET tracks = array_remove(tracks, {}) WHERE id = {};", self.id, track
        )
        await self.invalidate_cache(self.fetch_tracks, self.fetch_all, self.size, self.fetch_first, self.exists)

    async def remove_all_tracks(self) -> None:
        """Remove all tracks from the playlist."""
        await tables.PlaylistRow.raw("UPDATE player SET tracks = {} WHERE id = {};", [], self.id)
        await self.update_cache((self.fetch_tracks, []), (self.size, 0), (self.exists, True), (self.fetch_first, None))
        await self.invalidate_cache(self.fetch_all)

    async def delete(self) -> None:
        """Delete the playlist from the database"""
        await tables.PlaylistRow.raw("DELETE FROM playlist WHERE id = {}", self.id)
        await self.invalidate_cache()

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
        async with tables.DB.transaction():
            if self.id in BUNDLED_PLAYLIST_IDS:
                return False
            if requester.id in ((ids := getattr(bot, "owner_ids")) or ()) or requester.id == bot.owner_id:  # noqa
                return True
            elif await self.fetch_scope() == bot.user.id:
                return False
            return await self.fetch_author() == requester.id

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
        original_scope = await self.fetch_scope()
        if bot.user.id == original_scope:
            return f"(Global) {bot.user.mention}" if mention else f"(Global) {bot.user}"
        elif guild_ := bot.get_guild(original_scope):
            if guild_:
                guild = guild_
            return f"(Server) {guild.name}"
        elif guild and (channel := guild.get_channel_or_thread(original_scope)):
            return f"(Channel) {channel.mention}" if mention else f"(Channel) {channel.name}"

        elif (
            (guild := guild_ or guild)
            and (guild and (scope := guild.get_member(original_scope)))
            or (scope := bot.get_user(original_scope))
        ):
            return f"(User) {scope.mention}" if mention else f"(User) {scope}"
        else:
            return f"(Invalid) {original_scope}"

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
        author = await self.fetch_author()
        if user := bot.get_user(author):
            return f"{user.mention}" if mention else f"{user}"
        return f"{author}"

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
        name = BRACKETS.sub("", await self.fetch_name()).strip()
        if with_url:
            url = await self.fetch_url()
            if url and url.startswith("http"):
                return f"**[{discord.utils.escape_markdown(name)}]({url})**"
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
        data = await self.fetch_all()
        name = data["name"]
        compression = None
        with io.BytesIO() as bio:
            yaml.safe_dump(data, bio, default_flow_style=False, sort_keys=False, encoding="utf-8")
            bio.seek(0)
            LOGGER.debug("SIZE UNCOMPRESSED playlist (%s): %s", name, sys.getsizeof(bio))
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
                    LOGGER.debug("SIZE COMPRESSED playlist [%s] (%s): %s", compression, name, sys.getsizeof(bio))
                    yield bio, compression
                    return
            yield bio, compression

    async def bulk_update(self, scope: int, name: str, author: int, url: str | None, tracks: list[str]) -> None:
        """Bulk update the playlist."""
        await tables.PlaylistRow.raw(
            "INSERT INTO playlist  (id, name, author, scope, url, tracks) VALUES ({}, {}, {}, {}, {}, {}) "
            "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, author = EXCLUDED.author, scope = EXCLUDED.scope, "
            "url = EXCLUDED.url, tracks = EXCLUDED.tracks",
            self.id,
            name,
            author,
            scope,
            url,
            ujson.dumps(tracks),
        )
        await self.invalidate_cache()

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
            async with aiohttp.ClientSession(auto_decompress=False, json_serialize=ujson.dumps) as session:
                async with session.get(url) as response:
                    data = await response.read()
                    if ".gz.pylav" in url:
                        data = gzip.decompress(data)
                    elif ".br.pylav" in url:
                        data = brotli.decompress(data)
                    data = yaml.safe_load(data)
        except Exception as e:
            raise InvalidPlaylist(f"Invalid playlist file - {e}") from e
        playlist = cls(
            id=context.message.id,
        )
        await playlist.bulk_update(
            scope=scope, name=data["name"], url=data["url"], tracks=data["tracks"], author=context.author.id
        )
        return playlist

    async def fetch_index(self, index: int) -> str | None:
        """Get the track at the index.

        Parameters
        ----------
        index: int
            The index of the track

        Returns
        -------
        str
            The track at the index
        """
        if CACHING_ENABLED:
            tracks = await self.fetch_tracks()
            if index < 0:
                return random.choice(tracks) if tracks else None
            else:
                return tracks[index] if index < len(tracks) else None
        else:
            response = await tables.QueryRow.raw(
                "SELECT tracks->>{} as playlist FROM query WHERE id = {} LIMIT 1;", f"{index}", self.id
            )
            return response[0]["track"] if response else None

    @maybe_cached
    async def fetch_first(self) -> str | None:
        """Get the first track.

        Returns
        -------
        str
            The first track
        """
        response = await tables.QueryRow.raw("SELECT tracks->>0 as playlist FROM query WHERE id = {} LIMIT 1;", self.id)
        return response[0]["track"] if response else None

    async def fetch_random(self) -> str | None:
        """Get a random track.

        Returns
        -------
        str
            A random track
        """
        return await self.fetch_index(-1)


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class QueryModel(CachedModel, metaclass=_SingletonByKey):
    id: str

    @maybe_cached
    async def exists(self) -> bool:
        """Check if the config exists.

        Returns
        -------
        bool
            Whether the config exists.
        """
        return await tables.QueryRow.raw("SELECT EXISTS(SELECT 1 FROM query WHERE identifier = {});", self.id)

    async def delete(self):
        """Delete the query from the database"""
        await tables.QueryRow.raw("DELETE FROM query WHERE identifier = {}", self.id)
        await self.invalidate_cache()

    @maybe_cached
    async def size(self):
        """Count the tracks of the playlist.

        Returns
        -------
        int
            The number of tracks in the playlist.
        """
        response = await tables.QueryRow.raw(
            """SELECT jsonb_array_length(tracks) as size
        FROM query
        WHERE identifier = {}
        LIMIT 1;""",
            self.id,
        )
        return response[0]["size"] if response else 0

    @maybe_cached
    async def fetch_tracks(self) -> list[str]:
        """Get the tracks of the playlist.

        Returns
        -------
        list[str]
            The tracks of the playlist.
        """
        response = await tables.QueryRow.raw("SELECT tracks FROM query WHERE identifier = {} LIMIT 1;", self.id)
        return ujson.loads(response[0]["tracks"] if response else tables.QueryRow.tracks.default)

    async def update_tracks(self, tracks: list[str]):
        """Update the tracks of the playlist.

        Parameters
        ----------
        tracks: list[str]
            The tracks of the playlist.
        """
        await tables.QueryRow.raw(
            "INSERT INTO playlist (identifier, tracks) VALUES ({}, {}) ON CONFLICT (identifier) DO UPDATE SET tracks = "
            "EXCLUDED.tracks;",
            self.id,
            ujson.dumps(tracks),
        )
        await self.update_cache(
            (self.fetch_tracks, tracks),
            (self.size, len(tracks)),
            (self.fetch_first, tracks[0] if tracks else None),
            (self.exists, True),
        )

    @maybe_cached
    async def fetch_name(self) -> str:
        """Get the name of the playlist.

        Returns
        -------
        str
            The name of the playlist.
        """
        response = await tables.QueryRow.raw("SELECT name FROM query WHERE identifier = {} LIMIT 1;", self.id)
        return response[0]["name"] if response else tables.QueryRow.name.default

    async def update_name(self, name: str):
        """Update the name of the playlist.

        Parameters
        ----------
        name: str
            The name of the playlist.
        """
        await tables.QueryRow.raw(
            "INSERT INTO query (identifier, name) VALUES ({}, {}) ON CONFLICT (identifier) DO UPDATE SET name = "
            "EXCLUDED.name;",
            self.id,
            name,
        )
        await self.update_cache((self.fetch_name, name), (self.exists, True))

    @maybe_cached
    async def fetch_last_updated(self) -> datetime:
        """Get the last updated time of the playlist.

        Returns
        -------
        datetime
            The last updated time of the playlist.
        """
        response = await tables.QueryRow.raw("SELECT last_updated FROM query WHERE identifier = {} LIMIT 1;", self.id)
        return response[0]["last_updated"] if response else tables.QueryRow.last_updated.default

    async def update_last_updated(self):
        """Update the last updated time of the playlist"""
        await tables.QueryRow.raw(
            "INSERT INTO query (identifier, last_updated) "
            "VALUES ({}, {}) ON CONFLICT (identifier) "
            "DO UPDATE SET last_updated = EXCLUDED.last_updated;",
            self.id,
            tables.QueryRow.last_updated.default.python(),
        )
        await self.update_cache(
            (self.fetch_last_updated, tables.QueryRow.last_updated.default.python()), (self.exists, True)
        )

    async def bulk_update(self, tracks: list[str], name: str):
        """Bulk update the query.

        Parameters
        ----------
        tracks: list[str]
            The tracks of the playlist.
        name: str
            The name of the playlist
        """
        await tables.QueryRow.raw(
            "INSERT INTO query (identifier, tracks, name, last_updated) "
            "VALUES ({}, {}, {}, {}) ON CONFLICT (identifier) "
            "DO UPDATE SET tracks = EXCLUDED.tracks, name = EXCLUDED.name, last_updated = EXCLUDED.last_updated;",
            self.id,
            ujson.dumps(tracks),
            name,
            tables.QueryRow.last_updated.default.python(),
        )
        await self.update_cache(
            (self.fetch_tracks, tracks),
            (self.size, len(tracks)),
            (self.fetch_first, tracks[0] if tracks else None),
            (self.fetch_name, name),
            (self.fetch_last_updated, tables.QueryRow.last_updated.default.python()),
            (self.exists, True),
        )

    async def fetch_index(self, index: int) -> str | None:
        """Get the track at the index.

        Parameters
        ----------
        index: int
            The index of the track

        Returns
        -------
        str
            The track at the index
        """
        if CACHING_ENABLED:
            tracks = await self.fetch_tracks()
            if index < 0:
                return random.choice(tracks) if tracks else None
            else:
                return tracks[index] if index < len(tracks) else None
        else:
            response = await tables.QueryRow.raw(
                "SELECT tracks->>{} as query WHERE FROM query WHERE id = {} LIMIT 1;", f"{index}", self.id
            )
            return response[0]["track"] if response else None

    @maybe_cached
    async def fetch_first(self) -> str | None:
        """Get the first track.

        Returns
        -------
        str
            The first track
        """
        response = await tables.QueryRow.raw(
            "SELECT tracks->>0 as track FROM query WHERE identifier = {} LIMIT 1;", self.id
        )
        return response[0]["track"] if response else None

    async def fetch_random(self) -> str | None:
        """Get a random track.

        Returns
        -------
        str
            A random track
        """
        return await self.fetch_index(-1)


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
    pk = None

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
        """Delete the player state from the database"""
        await tables.PlayerStateRow.raw(
            """
            DELETE FROM player_state
            WHERE id = {} AND bot = {}
            """,
            self.id,
            self.bot,
        )

    async def save(self) -> None:
        """Save the player state to the database"""
        await tables.PlayerStateRow.raw(
            """
            INSERT INTO player_state (
                id,
                bot,
                channel_id,
                volume,
                position,
                auto_play_playlist_id,
                forced_channel_id,
                text_channel_id,
                notify_channel_id,
                paused,
                repeat_current,
                repeat_queue,
                shuffle,
                auto_shuffle,
                auto_play,
                playing,
                effect_enabled,
                self_deaf,
                current,
                queue,
                history,
                effects,
                extras
            )
            VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE
                SET channel_id = excluded.channel_id,
                    volume = excluded.volume,
                    position = excluded.position,
                    auto_play_playlist_id = excluded.auto_play_playlist_id,
                    forced_channel_id = excluded.forced_channel_id,
                    text_channel_id = excluded.text_channel_id,
                    notify_channel_id = excluded.notify_channel_id,
                    paused = excluded.paused,
                    repeat_current = excluded.repeat_current,
                    repeat_queue = excluded.repeat_queue,
                    shuffle = excluded.shuffle,
                    auto_shuffle = excluded.auto_shuffle,
                    auto_play = excluded.auto_play,
                    playing = excluded.playing,
                    effect_enabled = excluded.effect_enabled,
                    self_deaf = excluded.self_deaf,
                    current = excluded.current,
                    queue = excluded.queue,
                    history = excluded.history,
                    effects = excluded.effects,
                    extras = excluded.extras;
            """,
            self.id,
            self.bot,
            self.channel_id,
            self.volume,
            self.position,
            self.auto_play_playlist_id,
            self.forced_channel_id,
            self.text_channel_id,
            self.notify_channel_id,
            self.paused,
            self.repeat_current,
            self.repeat_queue,
            self.shuffle,
            self.auto_shuffle,
            self.auto_play,
            self.playing,
            self.effect_enabled,
            self.self_deaf,
            ujson.dumps(self.current),
            ujson.dumps(self.queue),
            ujson.dumps(self.history),
            ujson.dumps(self.effects),
            ujson.dumps(self.extras),
        )

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

        player = await tables.PlayerStateRow.raw(
            """SELECT id,
                bot,
                channel_id,
                volume,
                position,
                auto_play_playlist_id,
                forced_channel_id,
                text_channel_id,
                notify_channel_id,
                paused,
                repeat_current,
                repeat_queue,
                shuffle,
                auto_shuffle,
                auto_play,
                playing,
                effect_enabled,
                self_deaf,
                current,
                queue,
                history,
                effects,
                extras FROM player_state WHERE bot = {} AND id = {} LIMIT 1""",
            bot_id,
            guild_id,
        )
        return cls(**player[0]) if player else None


@dataclass(eq=True)
class EqualizerModel:
    id: int
    scope: int
    author: int
    name: str | None = None
    description: str | None = None
    band_25: float = 0.0
    band_40: float = 0.0
    band_63: float = 0.0
    band_100: float = 0.0
    band_160: float = 0.0
    band_250: float = 0.0
    band_400: float = 0.0
    band_630: float = 0.0
    band_1000: float = 0.0
    band_1600: float = 0.0
    band_2500: float = 0.0
    band_4000: float = 0.0
    band_6300: float = 0.0
    band_10000: float = 0.0
    band_16000: float = 0.0

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
        equalizer = await tables.EqualizerRow.raw(
            """
            SELECT * FROM equalizer WHERE id = {}
            LIMIT 1
            """,
            id,
        )
        return EqualizerModel(**equalizer[0]) if equalizer else None

    async def delete(self):
        """Delete the equalizer from the database"""
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
            async with aiohttp.ClientSession(auto_decompress=False, json_serialize=ujson.dumps) as session:
                async with session.get(url) as response:
                    data = await response.read()
                    if ".gz.pylav" in url:
                        data = gzip.decompress(data)
                    elif ".br.pylav" in url:
                        data = brotli.decompress(data)
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
