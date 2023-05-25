from __future__ import annotations

from asyncpg import Connection

from pylav.storage.migrations.logging import LOGGER


async def low_level_v_1_10_6_migration(con: Connection) -> None:
    """Run the low level migration for PyLav 1.10.6."""
    await low_level_v_1_10_6_queries(con)


async def low_level_v_1_10_6_queries(con: Connection) -> None:
    """Run the queries migration for PyLav 1.10.6."""
    await run_queries_migration_v_1_10_6(con)


async def run_queries_migration_v_1_10_6(con: Connection) -> None:
    """
    Add the info and pluginInfo columns to the query table.
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
            WHERE table_name='query' AND column_name='info')
            """
    has_column_response = await con.fetchval(has_column)
    if not has_column_response:
        LOGGER.info("----------- Migrating queries to PyLav 1.10.6 ---------")
        alter_table = """
        ALTER TABLE IF EXISTS query
        ADD COLUMN IF NOT EXISTS "info" jsonb DEFAULT NULL
        """
        await con.execute(alter_table)
