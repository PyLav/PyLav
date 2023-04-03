from __future__ import annotations

from asyncpg import Connection

from pylav.storage.migrations.logging import LOGGER


async def low_level_v_1_7_0_migration(con: Connection) -> None:
    """Run the low level migration for PyLav 1.7.0."""
    await low_level_v_1_7_0_tracks(con)
    await low_level_v_1_7_0_queries(con)


async def low_level_v_1_7_0_tracks(con: Connection) -> None:
    """Run the tracks migration for PyLav 1.7.0."""
    await run_tracks_migration_v_1_7_0(con)


async def low_level_v_1_7_0_queries(con: Connection) -> None:
    """Run the queries migration for PyLav 1.7.0."""
    await run_query_migration_v_1_7_0(con)


async def run_tracks_migration_v_1_7_0(con: Connection) -> None:
    """
    Add the info and pluginInfo columns to the tracks table.
    """
    has_column = """
        SELECT EXISTS (SELECT 1
        FROM information_schema.columns
        WHERE table_name='version' AND column_name='version')
        """
    has_version_column = await con.fetchval(has_column)
    if not has_version_column:
        return

    version = await con.fetchval("SELECT version from version;")
    if version is None:
        return

    has_column = """
            SELECT EXISTS (SELECT 1
            FROM information_schema.columns
            WHERE table_name='track' AND column_name='info')
            """
    has_column_response = await con.fetchval(has_column)
    if not has_column_response:
        LOGGER.info("----------- Migrating Tracks to PyLav 1.7.0 ---------")
        alter_table = """
        ALTER TABLE IF EXISTS track
        ADD COLUMN IF NOT EXISTS "info" jsonb,
        ADD COLUMN IF NOT EXISTS "pluginInfo" jsonb
        """
        await con.execute(alter_table)


async def run_query_migration_v_1_7_0(con: Connection) -> None:
    """
    Add the pluginInfo column to the query table.
    """
    has_column = """
        SELECT EXISTS (SELECT 1
        FROM information_schema.columns
        WHERE table_name='version' AND column_name='version')
        """
    has_version_column = await con.fetchval(has_column)
    if not has_version_column:
        return

    version = await con.fetchval("SELECT version from version;")
    if version is None:
        return

    has_column = """
            SELECT EXISTS (SELECT 1
            FROM information_schema.columns
            WHERE table_name='query' AND column_name='pluginInfo')
            """
    has_column_response = await con.fetchval(has_column)
    if not has_column_response:
        LOGGER.info("----------- Migrating Query to PyLav 1.7.0 ---------")
        alter_table = """
        ALTER TABLE IF EXISTS query
        ADD COLUMN IF NOT EXISTS "pluginInfo" jsonb
        """
        await con.execute(alter_table)
