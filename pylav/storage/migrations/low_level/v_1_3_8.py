from __future__ import annotations

from asyncpg import Connection


async def low_level_v_1_3_8_migration(con: Connection) -> None:
    await low_level_v_1_3_8_tracks(con)


async def low_level_v_1_3_8_tracks(con: Connection) -> None:
    await run_tracks_migration_v_1_3_8(con)


async def run_tracks_migration_v_1_3_8(con: Connection) -> None:
    """
    Add the Artwork column to the tracks table.
    """
    version = await con.fetchval("SELECT version from version;")
    if version is None:
        return

    has_column = """
            SELECT EXISTS (SELECT 1
            FROM information_schema.columns
            WHERE table_name='track' AND column_name='artwork')
            """
    has_artwork = await con.fetchval(has_column)
    if not has_artwork:
        alter_table = """
        ALTER TABLE IF EXISTS track
        ADD COLUMN IF NOT EXISTS artwork text COLLATE pg_catalog."default"
        """
        await con.execute(alter_table)
