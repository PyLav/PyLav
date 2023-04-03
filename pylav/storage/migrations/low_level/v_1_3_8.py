from __future__ import annotations

from asyncpg import Connection

from pylav.storage.migrations.logging import LOGGER


async def low_level_v_1_3_8_migration(con: Connection) -> None:
    """Run the low level migration for PyLav 1.3.8."""
    await low_level_v_1_3_8_tracks(con)


async def low_level_v_1_3_8_tracks(con: Connection) -> None:
    """Run the tracks migration for PyLav 1.3.8."""
    await run_tracks_migration_v_1_3_8(con)


async def run_tracks_migration_v_1_3_8(con: Connection) -> None:
    """
    Add the Artwork column to the tracks table.
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
            WHERE table_name='track' AND column_name='artworkUrl')
            """
    has_artwork = await con.fetchval(has_column)
    if not has_artwork:
        LOGGER.info("----------- Migrating Tracks to PyLav 1.3.8 ---------")
        alter_table = """
        ALTER TABLE IF EXISTS track
        ADD COLUMN IF NOT EXISTS "artworkUrl" text COLLATE pg_catalog."default"
        """
        await con.execute(alter_table)
