# sourcery skip: avoid-builtin-shadow
from __future__ import annotations

import os

from piccolo.columns import JSONB, UUID, Array, BigInt, Boolean, Bytea, Float, Integer, Text, Timestamptz
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.engine import PostgresEngine, SQLiteEngine
from piccolo.table import Table
from piccolo.utils.pydantic import create_pydantic_model

from pylav._config import CONFIG_DIR
from pylav._logging import getLogger
from pylav.envvars import (
    POSTGRES_DATABASE,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
    USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE,
    USE_BUNDLED_EXTERNAL_PYLAV_NODE,
)
from pylav.migrations import run_low_level_migrations

LOGGER = getLogger("PyLav.Postgres")
config = {
    "host": POSTGRES_HOST,
    "port": int(POSTGRES_PORT) if isinstance(POSTGRES_PORT, str) else POSTGRES_PORT,
    "database": POSTGRES_DATABASE,
    "user": POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
}
LOGGER.info("Connecting to Postgres server using %r", config)
if os.getenv("BUILDING_DOCS", False):
    DB = SQLiteEngine()
else:
    DB = PostgresEngine(config=config)

run_low_level_migrations(DB)


class PlaylistRow(Table, db=DB, tablename="playlist"):
    id = BigInt(primary_key=True)
    scope = BigInt(null=True, default=None)
    author = BigInt(null=True, default=None)
    name = Text(null=True, default=None)
    url = Text(null=True, default=None)
    tracks = JSONB(null=False, default=[])


class LibConfigRow(Table, db=DB, tablename="lib_config"):
    id = BigInt(index=True)
    bot = BigInt(primary_key=True, index=True)
    config_folder = Text(null=False, default=str(CONFIG_DIR))
    java_path = Text(null=False, default="java")
    enable_managed_node = Boolean(null=False, default=True)
    auto_update_managed_nodes = Boolean(null=False, default=True)
    localtrack_folder = Text(null=True, default=str(CONFIG_DIR / "music"))
    download_id = BigInt(index=True, default=0)
    update_bot_activity = Boolean(null=False, default=False)
    use_bundled_pylav_external = Boolean(null=False, default=USE_BUNDLED_EXTERNAL_PYLAV_NODE)
    use_bundled_lava_link_external = Boolean(null=False, default=USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE)

    extras: JSONB = JSONB(null=False, default={})
    next_execution_update_bundled_playlists = Timestamptz(null=True, default=None)
    next_execution_update_bundled_external_playlists = Timestamptz(null=True, default=None)
    next_execution_update_external_playlists = Timestamptz(null=True, default=None)


class EqualizerRow(Table, db=DB, tablename="equalizer"):
    id = BigInt(primary_key=True, index=True)
    scope = BigInt(null=True, default=None)
    name = Text(null=True, default=None)
    description = Text(null=True, default=None)
    author = BigInt(null=True, default=None)
    band_25 = Float(null=False, default=0.0)
    band_40 = Float(null=False, default=0.0)
    band_63 = Float(null=False, default=0.0)
    band_100 = Float(null=False, default=0.0)
    band_160 = Float(null=False, default=0.0)
    band_250 = Float(null=False, default=0.0)
    band_400 = Float(null=False, default=0.0)
    band_630 = Float(null=False, default=0.0)
    band_1000 = Float(null=False, default=0.0)
    band_1600 = Float(null=False, default=0.0)
    band_2500 = Float(null=False, default=0.0)
    band_4000 = Float(null=False, default=0.0)
    band_6300 = Float(null=False, default=0.0)
    band_10000 = Float(null=False, default=0.0)
    band_16000 = Float(null=False, default=0.0)


class PlayerStateRow(Table, db=DB, tablename="player_state"):
    primary_key = UUID(primary_key=True)
    id = BigInt(index=True, null=False)
    bot = BigInt(index=True, null=False)
    channel_id = BigInt(null=True, default=None)
    volume = Integer(null=False, default=100)
    position = Float(null=False, default=0.0)
    auto_play_playlist_id = BigInt(null=True, default=1)
    forced_channel_id = BigInt(null=True, default=0)
    text_channel_id = BigInt(null=True, default=0)
    notify_channel_id = BigInt(null=True, default=0)

    paused = Boolean(null=False, default=False)
    repeat_current = Boolean(null=False, default=False)
    repeat_queue = Boolean(null=False, default=False)
    shuffle = Boolean(null=False, default=True)
    auto_shuffle = Boolean(null=False, default=False)
    auto_play = Boolean(null=False, default=False)
    playing = Boolean(null=False, default=False)
    effect_enabled = Boolean(null=False, default=False)
    self_deaf = Boolean(null=False, default=False)

    current = JSONB(null=True, default={})
    queue = JSONB(null=False, default=[])
    history = JSONB(null=False, default=[])
    effects = JSONB(null=False, default={})
    extras = JSONB(null=False, default={})


class PlayerRow(Table, db=DB, tablename="player"):
    primary_key = UUID(primary_key=True)
    id = BigInt(index=True)
    bot = BigInt(index=True, null=False)
    volume = Integer(null=False, default=100)
    max_volume = Integer(null=False, default=1000)
    auto_play_playlist_id = BigInt(null=False, default=1)

    text_channel_id = BigInt(null=True, default=0)
    notify_channel_id = BigInt(null=True, default=0)
    forced_channel_id = BigInt(null=True, default=0)

    repeat_current = Boolean(null=False, default=False)
    repeat_queue = Boolean(null=False, default=False)
    shuffle = Boolean(null=False, default=True)
    auto_shuffle = Boolean(null=False, default=True)
    auto_play = Boolean(null=False, default=True)
    self_deaf = Boolean(null=False, default=True)
    empty_queue_dc = JSONB(
        null=False,
        default={
            "enabled": False,
            "time": 60,
        },
    )
    alone_dc = JSONB(
        null=False,
        default={
            "enabled": False,
            "time": 60,
        },
    )
    alone_pause = JSONB(
        null=False,
        default={
            "enabled": False,
            "time": 60,
        },
    )
    extras = JSONB(null=False, default={})
    effects = JSONB(null=False, default={})
    dj_users = Array(null=False, default=[], base_column=BigInt())
    dj_roles = Array(null=False, default=[], base_column=BigInt())


class NodeRow(Table, db=DB, tablename="node"):
    id = BigInt(primary_key=True, index=True)
    name = Text(null=False)
    ssl = Boolean(null=False, default=False)
    resume_key = Text(null=True, default=None)
    resume_timeout = Integer(null=False, default=600)
    reconnect_attempts = Integer(null=False, default=-1)
    search_only = Boolean(null=False, default=False)
    managed = Boolean(null=False, default=False)
    disabled_sources = Array(null=False, default=[], base_column=Text())
    extras = JSONB(null=True, default={})
    yaml = JSONB(null=True, default={})


class QueryRow(Table, db=DB, tablename="query"):
    identifier = Text(null=False, index=True, primary_key=True)
    name = Text(null=True, default=None)
    tracks = JSONB(null=False, default=[])
    last_updated = Timestamptz(null=False, index=True, default=TimestamptzNow())


class BotVersionRow(Table, db=DB, tablename="version"):
    bot = BigInt(primary_key=True, index=True)
    version = Text(null=False, default="0.0.0")


class AioHttpCacheRow(Table, db=DB, tablename="aiohttp_client_cache"):
    key = Text(primary_key=True, index=True)
    value = Bytea()


PlaylistPDModel = create_pydantic_model(PlaylistRow)
LibConfigPDModel = create_pydantic_model(LibConfigRow)
EqualizerPDModel = create_pydantic_model(EqualizerRow)
PlayerStatePDModel = create_pydantic_model(PlayerStateRow)
PlayerPDModel = create_pydantic_model(PlayerRow)
NodePDModel = create_pydantic_model(NodeRow)
QueryPDModel = create_pydantic_model(QueryRow)
BotVersioPDModel = create_pydantic_model(BotVersionRow)
AioHttpCachePDModel = create_pydantic_model(AioHttpCacheRow)
