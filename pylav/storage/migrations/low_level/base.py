from __future__ import annotations

from typing import TYPE_CHECKING

import asyncpg

from pylav.storage.database.tables.misc import DATABASE_ENGINE
from pylav.storage.migrations.logging import LOGGER
from pylav.storage.migrations.low_level.v_1_0_0 import (
    low_level_v_1_0_0_migration,
    migrate_lib_config_v_1_0_0,
    migrate_node_config_v_1_0_0,
    migrate_player_config_v_1_0_0,
    migrate_playlists_v_1_0_0,
    migrate_queries_v_1_0_0,
)
from pylav.storage.migrations.low_level.v_1_3_8 import low_level_v_1_3_8_migration
from pylav.storage.migrations.low_level.v_1_7_0 import low_level_v_1_7_0_migration
from pylav.storage.migrations.low_level.v_1_10_6 import low_level_v_1_10_6_migration

if TYPE_CHECKING:
    from pylav.storage.controllers.config import ConfigController


async def run_low_level_migrations(migrator: ConfigController) -> dict[str, dict[str, list[asyncpg.Record] | None]]:
    """
    Runs migrations.
    """
    migration_data = {}
    con = await DATABASE_ENGINE.get_new_connection()
    await low_level_v_1_0_0_migration(con, migration_data, migrator)
    await low_level_v_1_3_8_migration(con)
    await low_level_v_1_7_0_migration(con)
    await low_level_v_1_10_6_migration(con)
    return migration_data


async def migrate_data(data: dict[str, dict[str, list[asyncpg.Record]]]) -> None:
    """
    Migrates data.
    """

    for version, migrations in data.items():
        match version:
            case "1.0.0":
                if "playlist" in migrations and migrations["playlist"]:
                    LOGGER.info("----------- Migrating Playlist data to PyLav 1.0.0 ---------")
                    await migrate_playlists_v_1_0_0(migrations["playlist"])
                if "query" in migrations and migrations["query"]:
                    LOGGER.info("----------- Migrating Query data to PyLav 1.0.0 ---------")
                    await migrate_queries_v_1_0_0(migrations["query"])
                if "player" in migrations and migrations["player"]:
                    LOGGER.info("----------- Migrating Player settings to PyLav 1.0.0 ---------")
                    await migrate_player_config_v_1_0_0(migrations["player"])
                if "lib" in migrations and migrations["lib"]:
                    LOGGER.info("----------- Migrating Lib settings to PyLav 1.0.0 ---------")
                    await migrate_lib_config_v_1_0_0(migrations["lib"])
                if "node" in migrations and migrations["node"]:
                    LOGGER.info("----------- Migrating Node settings to PyLav 1.0.0 ---------")
                    await migrate_node_config_v_1_0_0(migrations["node"])
