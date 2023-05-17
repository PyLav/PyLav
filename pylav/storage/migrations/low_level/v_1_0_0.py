from __future__ import annotations

import contextlib
from collections import defaultdict
from typing import TYPE_CHECKING

import asyncpg
from asyncpg import Connection
from dacite import from_dict
from packaging.version import parse

from pylav.compat import json
from pylav.constants.playlists import BUNDLED_PLAYLIST_IDS
from pylav.constants.versions import VERSION_1_0_0
from pylav.nodes.api.responses.track import Track
from pylav.players.tracks.decoder import decode_track
from pylav.storage.database.tables.config import LibConfigRow
from pylav.storage.database.tables.nodes import NodeRow
from pylav.storage.database.tables.players import PlayerRow
from pylav.storage.database.tables.playlists import PlaylistRow
from pylav.storage.database.tables.queries import QueryRow
from pylav.storage.database.tables.tracks import TrackRow

if TYPE_CHECKING:
    from pylav.storage.controllers.config import ConfigController


async def run_playlist_migration_v_1_0_0(connection: Connection) -> list[asyncpg.Record]:
    """
    Runs playlist migration 100.
    """
    HAS_COLUMN = """
    SELECT EXISTS (SELECT 1
    FROM information_schema.columns
    WHERE table_name='playlist' AND column_name='tracks')
    """
    has_playlist_tracks = await connection.fetchval(HAS_COLUMN)
    if has_playlist_tracks:
        data = await connection.fetch("SELECT * FROM playlist;")
        await connection.execute("DROP TABLE playlist;")
        return data


async def run_query_migration_v_1_0_0(connection: Connection) -> list[asyncpg.Record] | None:
    """
    Runs playlist migration 100.
    """
    HAS_COLUMN = """
    SELECT EXISTS (SELECT 1
    FROM information_schema.columns
    WHERE table_name='query' AND column_name='tracks')
    """
    has_query_tracks = await connection.fetchval(HAS_COLUMN)
    if has_query_tracks:
        data = await connection.fetch("SELECT * FROM query;")
        await connection.execute("DROP TABLE query;")
        return data


async def run_player_config_v_1_0_0(connection: Connection) -> list[asyncpg.Record]:
    """
    Migrates player config.
    """
    has_column = """
    SELECT EXISTS (SELECT 1
    FROM information_schema.columns
    WHERE table_name='version' AND column_name='version')
    """
    has_version_column = await connection.fetchval(has_column)
    if not has_version_column:
        return []
    version = await connection.fetchval("SELECT version from version;")
    if version is None:
        return []

    version = parse(version)
    if (not version) or version < VERSION_1_0_0:
        return await connection.fetch("SELECT * FROM player;")
    return []


async def run_node_config_v_1_0_0(connection: Connection) -> list[asyncpg.Record]:
    """
    Migrates player config.
    """
    has_column = """
    SELECT EXISTS (SELECT 1
    FROM information_schema.columns
    WHERE table_name='version' AND column_name='version')
    """
    has_version_column = await connection.fetchval(has_column)
    if not has_version_column:
        return []
    version = await connection.fetchval("SELECT version from version;")
    if version is None:
        return []

    version = parse(version)
    if (not version) or version < VERSION_1_0_0:
        return await connection.fetch("SELECT * FROM node;")
    return []


async def run_lib_config_v_1_0_0(connection: Connection) -> list[asyncpg.Record]:
    """
    Migrates player config.
    """
    has_column = """
    SELECT EXISTS (SELECT 1
    FROM information_schema.columns
    WHERE table_name='version' AND column_name='version')
    """
    has_version_column = await connection.fetchval(has_column)
    if not has_version_column:
        return []
    version = await connection.fetchval("SELECT version from version;")
    if version is None:
        return []

    version = parse(version)
    if (not version) or version < VERSION_1_0_0:
        return await connection.fetch("SELECT * FROM lib_config;")


async def migrate_playlists_v_1_0_0(playlists: list[asyncpg.Record]) -> None:
    """Runs playlist migration for version 1.0.0."""
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
        _temp = defaultdict(list)
        for x in tracks:
            _temp[type(x)].append(x)
        for entry_type, entry_list in _temp.items():
            if entry_type == str:
                for track in entry_list:
                    with contextlib.suppress(Exception):
                        # TODO: Make an API call to the public node?
                        new_tracks.append(await TrackRow.get_or_create(decode_track(track)))
            elif entry_type == dict:
                for track_object in entry_list:
                    new_tracks.append(await TrackRow.get_or_create(from_dict(data_class=Track, data=track_object)))
            else:
                for track_object in entry_list:
                    new_tracks.append(await TrackRow.get_or_create(track_object))
        if new_tracks:
            await playlist_row.add_m2m(*new_tracks, m2m=PlaylistRow.tracks)


async def migrate_queries_v_1_0_0(queries: list[asyncpg.Record]) -> None:
    """Processes queries for migration to version 1.0.0."""
    for query in queries:
        defaults = {QueryRow.name: query["name"]}
        query_row = await QueryRow.objects().get_or_create(QueryRow.identifier == query["identifier"], defaults)

        # noinspection PyProtectedMember
        if not query_row._was_created:
            await QueryRow.update(defaults).where(QueryRow.identifier == query["identifier"])
        new_tracks = []
        # TODO: Optimize this, after https://github.com/piccolo-orm/piccolo/discussions/683 is answered or fixed
        tracks = json.loads(query["tracks"]) if query["tracks"] else []
        _temp = defaultdict(list)
        for x in tracks:
            _temp[type(x)].append(x)
        for entry_type, entry_list in _temp.items():
            if entry_type == str:
                for track in entry_list:
                    with contextlib.suppress(Exception):
                        # TODO: Make an API call to the public node?
                        new_tracks.append(await TrackRow.get_or_create(decode_track(track)))
            elif entry_type == dict:
                for track_object in entry_list:
                    new_tracks.append(await TrackRow.get_or_create(from_dict(data_class=Track, data=track_object)))
            else:
                for track_object in entry_list:
                    new_tracks.append(await TrackRow.get_or_create(track_object))
        if new_tracks:
            await query_row.add_m2m(*new_tracks, m2m=QueryRow.tracks)


async def migrate_player_config_v_1_0_0(players: list[asyncpg.Record]) -> None:
    """Processes player config for migration to version 1.0.0."""
    bulk_insert = []
    for player in players:
        data = {
            "id": player["id"],
            "bot": player["bot"],
            "volume": player["volume"],
            "max_volume": player["max_volume"],
            "auto_play_playlist_id": player["auto_play_playlist_id"],
            "text_channel_id": player["text_channel_id"],
            "notify_channel_id": player["notify_channel_id"],
            "forced_channel_id": player["forced_channel_id"],
            "repeat_current": player["repeat_current"],
            "repeat_queue": player["repeat_queue"],
            "shuffle": player["shuffle"],
            "auto_shuffle": player["auto_shuffle"],
            "auto_play": player["auto_play"],
            "self_deaf": player["self_deaf"],
            "empty_queue_dc": json.loads(player["empty_queue_dc"]),
            "alone_dc": json.loads(player["alone_dc"]),
            "alone_pause": json.loads(player["alone_pause"]),
            "extras": json.loads(player["extras"]),
            "effects": json.loads(player["effects"]),
            "dj_users": player["dj_users"],
            "dj_roles": player["dj_roles"],
        }

        if player["id"] == 0:
            data = {
                PlayerRow.volume: player["volume"],
                PlayerRow.max_volume: player["max_volume"],
                PlayerRow.auto_play_playlist_id: player["auto_play_playlist_id"],
                PlayerRow.text_channel_id: player["text_channel_id"],
                PlayerRow.notify_channel_id: player["notify_channel_id"],
                PlayerRow.forced_channel_id: player["forced_channel_id"],
                PlayerRow.repeat_current: player["repeat_current"],
                PlayerRow.repeat_queue: player["repeat_queue"],
                PlayerRow.shuffle: player["shuffle"],
                PlayerRow.auto_shuffle: player["auto_shuffle"],
                PlayerRow.auto_play: player["auto_play"],
                PlayerRow.self_deaf: player["self_deaf"],
                PlayerRow.empty_queue_dc: json.loads(player["empty_queue_dc"]),
                PlayerRow.alone_dc: json.loads(player["alone_dc"]),
                PlayerRow.alone_pause: json.loads(player["alone_pause"]),
                PlayerRow.extras: json.loads(player["extras"]),
                PlayerRow.effects: json.loads(player["effects"]),
                PlayerRow.dj_users: player["dj_users"],
                PlayerRow.dj_roles: player["dj_roles"],
            }

            playerobj = await PlayerRow.objects().get_or_create(
                (PlayerRow.id == player["id"]) & (PlayerRow.bot == player["bot"]), defaults=data
            )
            if not playerobj._was_created:
                await PlayerRow.update(data).where((PlayerRow.id == player["id"]) & (PlayerRow.bot == player["bot"]))

        else:
            bulk_insert.append(PlayerRow(**data))
    if bulk_insert:
        await PlayerRow.insert(*bulk_insert)


async def migrate_node_config_v_1_0_0(nodes: list[asyncpg.Record]) -> None:
    """Processes node config for migration to version 1.0.0."""
    for node in nodes:
        data = {
            NodeRow.name: node["name"],
            NodeRow.ssl: node["ssl"],
            NodeRow.resume_timeout: node["resume_timeout"],
            NodeRow.reconnect_attempts: node["reconnect_attempts"],
            NodeRow.search_only: node["search_only"],
            NodeRow.managed: node["managed"],
            NodeRow.disabled_sources: node["disabled_sources"],
            NodeRow.extras: json.loads(node["extras"]),
            NodeRow.yaml: json.loads(node["yaml"]),
        }
        node_obj = await NodeRow.objects().get_or_create(NodeRow.id == node["id"], defaults=data)
        if not node_obj._was_created:
            await NodeRow.update(data).where(NodeRow.id == node["id"])


async def migrate_lib_config_v_1_0_0(configs: list[asyncpg.Record]) -> None:
    """Processes lib config for migration to version 1.0.0."""
    for config in configs:
        data = {
            LibConfigRow.config_folder: config["config_folder"],
            LibConfigRow.java_path: config["java_path"],
            LibConfigRow.enable_managed_node: config["enable_managed_node"],
            LibConfigRow.auto_update_managed_nodes: config["auto_update_managed_nodes"],
            LibConfigRow.localtrack_folder: config["localtrack_folder"],
            LibConfigRow.download_id: config["download_id"],
            LibConfigRow.update_bot_activity: config["update_bot_activity"],
            LibConfigRow.use_bundled_pylav_external: config["use_bundled_pylav_external"],
            LibConfigRow.use_bundled_lava_link_external: False,
            LibConfigRow.extras: json.loads(config["extras"]),
            LibConfigRow.next_execution_update_bundled_playlists: config["next_execution_update_bundled_playlists"],
            LibConfigRow.next_execution_update_bundled_external_playlists: config[
                "next_execution_update_bundled_external_playlists"
            ],
            LibConfigRow.next_execution_update_external_playlists: config["next_execution_update_external_playlists"],
        }
        config_obj = await LibConfigRow.objects().get_or_create(
            (LibConfigRow.id == config["id"]) & (LibConfigRow.bot == config["bot"]), defaults=data
        )
        if not config_obj._was_created:
            await LibConfigRow.update(data).where(
                (LibConfigRow.id == config["id"]) & (LibConfigRow.bot == config["bot"])
            )


async def low_level_v_1_0_0_migration(
    con: Connection, migration_data: dict[str, dict[str, list[asyncpg.Record]] | None], migrator: ConfigController
) -> None:
    """Runs the low level migration for version 1.0.0."""
    version = "1.0.0"
    migration_data[version] = {}
    await low_level_v_1_0_0_playlists(con, migration_data, version)
    await low_level_v_1_0_0_queries(con, migration_data, version)
    await low_level_v_1_0_0_players(con, migration_data, version)
    await low_level_v_1_0_0_lib(con, migration_data, version)
    await low_level_v_1_0_0_nodes(con, migration_data, version)
    if migration_data[version]:
        await migrator.reset_database()


async def low_level_v_1_0_0_nodes(
    con: Connection, migration_data: dict[str, dict[str, list[asyncpg.Record]] | None], version: str
) -> None:
    """Runs the low level migration of nodes  for version 1.0.0."""
    node_config_data_1000 = await run_node_config_v_1_0_0(con)
    if node_config_data_1000:
        migration_data[version]["node"] = node_config_data_1000


async def low_level_v_1_0_0_lib(
    con: Connection, migration_data: dict[str, dict[str, list[asyncpg.Record]] | None], version: str
) -> None:
    """Runs the low level migration of lib config for version 1.0.0."""
    lib_config_data_1000 = await run_lib_config_v_1_0_0(con)
    if lib_config_data_1000:
        migration_data[version]["lib"] = lib_config_data_1000


async def low_level_v_1_0_0_players(
    con: Connection, migration_data: dict[str, dict[str, list[asyncpg.Record]] | None], version: str
) -> None:
    """Runs the low level migration of players for version 1.0.0."""
    player_data_1000 = await run_player_config_v_1_0_0(con)
    if player_data_1000:
        migration_data[version]["player"] = player_data_1000


async def low_level_v_1_0_0_queries(
    con: Connection, migration_data: dict[str, dict[str, list[asyncpg.Record]] | None], version: str
) -> None:
    """Runs the low level migration of queries for version 1.0.0."""
    query_data_1000 = await run_query_migration_v_1_0_0(con)
    if query_data_1000:
        migration_data[version]["query"] = query_data_1000


async def low_level_v_1_0_0_playlists(
    con: Connection, migration_data: dict[str, dict[str, list[asyncpg.Record]] | None], version: str
) -> None:
    """Runs the low level migration of playlists for version 1.0.0."""
    playlist_data_1000 = await run_playlist_migration_v_1_0_0(con)
    if playlist_data_1000:
        migration_data[version]["playlist"] = playlist_data_1000
