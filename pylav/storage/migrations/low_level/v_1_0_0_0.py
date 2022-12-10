from __future__ import annotations

import contextlib
import json

import asyncpg
from asyncpg import Connection

from pylav.constants.playlists import BUNDLED_PLAYLIST_IDS
from pylav.constants.versions import VERSION_1_0_0_0
from pylav.players.tracks.decoder import async_decoder
from pylav.storage.database.tables.misc import DATABASE_ENGINE
from pylav.storage.database.tables.playlists import PlaylistRow
from pylav.storage.database.tables.queries import QueryRow
from pylav.storage.database.tables.tracks import TrackRow
from pylav.storage.migrations.logging import LOGGER
from pylav.utils.vendor.redbot import AsyncIter


async def run_playlist_migration_v_1_0_0_0(connection: Connection) -> list[asyncpg.Record]:
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


async def run_player_state_migration_v_1_0_0_0(connection: Connection) -> None:
    """
    Runs player_state migration 1000.
    """
    await connection.execute("DROP TABLE player_state;")


async def run_query_migration_v_1_0_0_0(connection: Connection) -> list[asyncpg.Record] | None:
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


async def migrate_playlists_v_1_0_0_0(playlists: list[asyncpg.Record]) -> None:
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
        # noinspection PyProtectedMember
        if not playlist_row._was_created:
            await PlaylistRow.update(defaults).where(PlaylistRow.id == playlist["id"])
        new_tracks = []
        # TODO: Optimize this, after https://github.com/piccolo-orm/piccolo/discussions/683 is answered or fixed
        tracks = json.loads(playlist["tracks"]) if playlist["tracks"] else []
        async for track in AsyncIter(tracks):
            with contextlib.suppress(Exception):
                data = await async_decoder(track)
                new_tracks.append(await TrackRow.get_or_create(data.encoded, data.info.to_database()))
        if new_tracks:
            await playlist_row.add_m2m(*new_tracks, m2m=PlaylistRow.tracks)


async def migrate_queries_v_1_0_0_0(queries: list[asyncpg.Record]) -> None:

    for query in queries:
        defaults = {QueryRow.name: query["name"]}
        query_row = await QueryRow.objects().get_or_create(QueryRow.identifier == query["identifier"], defaults)

        # noinspection PyProtectedMember
        if not query_row._was_created:
            await QueryRow.update(defaults).where(QueryRow.identifier == query["identifier"])
        new_tracks = []
        # TODO: Optimize this, after https://github.com/piccolo-orm/piccolo/discussions/683 is answered or fixed
        tracks = json.loads(query["tracks"]) if query["tracks"] else []
        async for track in AsyncIter(tracks):
            with contextlib.suppress(Exception):
                data = await async_decoder(track)
                new_tracks.append(await TrackRow.get_or_create(data.encoded, data.info.to_database()))
        if new_tracks:
            await query_row.add_m2m(*new_tracks, m2m=QueryRow.tracks)


async def run_low_level_migrations() -> dict[str, dict[str, list[asyncpg.Record]]]:
    """
    Runs migrations.
    """

    con: Connection = await DATABASE_ENGINE.get_new_connection()
    playlist_data_1000 = await run_playlist_migration_v_1_0_0_0(con)
    query_data_1000 = await run_query_migration_v_1_0_0_0(con)
    if playlist_data_1000 or query_data_1000:
        await run_player_state_migration_v_1_0_0_0(con)
    return {
        VERSION_1_0_0_0: {
            "playlist": playlist_data_1000,
            "query": query_data_1000,
        }
    }


async def migrate_data(data: dict[str, dict[str, list[asyncpg.Record]]]) -> None:
    """
    Migrates data.
    """

    for version, migrations in data.items():
        LOGGER.info(f"Running migrations for version {version}")
        match version:
            case "1000":
                if migrations["playlist"] is not None:
                    await migrate_playlists_v_1_0_0_0(migrations["playlist"])
                if migrations["query"] is not None:
                    await migrate_queries_v_1_0_0_0(migrations["query"])
