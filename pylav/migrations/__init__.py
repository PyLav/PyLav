from __future__ import annotations

import asyncio
import contextlib
import json

import asyncpg
from asyncpg import Connection


async def run_playlist_migration_1000(connection: Connection):
    """
    Runs playlist migration 1000.
    """
    HAS_COLUMN = """
    SELECT EXISTS (SELECT 1
    FROM information_schema.columns
    WHERE table_name='playlist' AND column_name='tracks')
    """
    has_playlist_tracks = await connection.fetchval(HAS_COLUMN)
    if has_playlist_tracks:
        data = await connection.fetch(
            """
            SELECT * FROM playlist;
            """
        )
        await connection.execute("DROP TABLE playlist;")
        return data


async def run_player_state_migration_1000(connection: Connection):
    """
    Runs player_state migration 1000.
    """
    await connection.execute("DROP TABLE player_state;")


async def run_query_migration_1000(connection: Connection):
    """
    Runs playlist migration 1000.
    """
    HAS_COLUMN = """
        SELECT EXISTS (SELECT 1
        FROM information_schema.columns
        WHERE table_name='query' AND column_name='tracks')
        """
    has_query_tracks = await connection.fetchval(HAS_COLUMN)
    if has_query_tracks:
        data = await connection.fetch(
            """
        SELECT * FROM query;
        """
        )
        await connection.execute("DROP TABLE query;")
        return data


async def migrate_playlists(playlists: list[asyncpg.Record]):
    from pylav.constants import BUNDLED_PLAYLIST_IDS
    from pylav.sql.tables.playlists import PlaylistRow
    from pylav.sql.tables.tracks import TrackRow
    from pylav.track_encoding import decode_track
    from pylav.utils import AsyncIter

    for playlist in playlists:
        if playlist["id"] in BUNDLED_PLAYLIST_IDS:
            continue
        defaults = {
            PlaylistRow.name: playlist["name"],
            PlaylistRow.scope: playlist["scope"],
            PlaylistRow.author: playlist["author"],
            PlaylistRow.url: playlist["url"],
        }
        playlist_row = await PlaylistRow.objects().get_or_create(PlaylistRow.id == playlist["id"], defaults)
        if not playlist_row._was_created:
            await PlaylistRow.update(defaults).where(PlaylistRow.id == playlist["id"])
        new_tracks = []
        # TODO: Optimize this, after https://github.com/piccolo-orm/piccolo/discussions/683 is answered or fixed
        playlist["tracks"] = json.loads(playlist["tracks"]) if playlist["tracks"] else []
        async for track in AsyncIter(playlist["tracks"]):
            with contextlib.suppress(Exception):
                data, _ = await asyncio.to_thread(decode_track, track)
                new_tracks.append(await TrackRow.get_or_create(data.encoded, data.info.to_database()))
        if new_tracks:
            await playlist_row.add_m2m(*new_tracks, m2m=PlaylistRow.tracks)


async def migrate_queries(queries: list[asyncpg.Record]):
    from pylav.sql.tables.queries import QueryRow
    from pylav.sql.tables.tracks import TrackRow
    from pylav.track_encoding import decode_track
    from pylav.utils import AsyncIter

    for query in queries:
        defaults = {QueryRow.name: query["name"]}
        query_row = await QueryRow.objects().get_or_create(QueryRow.identifier == query["identifier"], defaults)
        if not query_row._was_created:
            await QueryRow.update(defaults).where(QueryRow.identifier == query["identifier"])
        new_tracks = []
        # TODO: Optimize this, after https://github.com/piccolo-orm/piccolo/discussions/683 is answered or fixed
        query["tracks"] = json.loads(query["tracks"]) if query["tracks"] else []
        async for track in AsyncIter(query["tracks"]):
            with contextlib.suppress(Exception):
                data, _ = await asyncio.to_thread(decode_track, track)
                new_tracks.append(await TrackRow.get_or_create(data.encoded, data.info.to_database()))
        if new_tracks:
            await query_row.add_m2m(*new_tracks, m2m=QueryRow.tracks)


async def run_low_level_migrations():
    """
    Runs migrations.
    """
    from pylav.sql.tables.init import IS_POSTGRES

    if not IS_POSTGRES:
        return
    from pylav.sql.tables.init import DB

    con: Connection = await DB.get_new_connection()
    playlist_data_1000 = await run_playlist_migration_1000(con)
    query_data_1000 = await run_query_migration_1000(con)
    if playlist_data_1000 or query_data_1000:
        await run_player_state_migration_1000(con)
    return {
        "playlist_1000": playlist_data_1000,
        "query_1000": query_data_1000,
    }


async def migrate_data(data: dict) -> None:
    """
    Migrates data.
    """
    from pylav._logging import getLogger

    LOGGER = getLogger("PyLav.sql.migrations")
    if data["query_1000"]:
        LOGGER.info("Migrating queries to new schema...")
        await migrate_queries(data["query_1000"])
    if data["playlist_1000"]:
        LOGGER.info("Migrating playlists to new schema...")
        await migrate_playlists(data["playlist_1000"])
