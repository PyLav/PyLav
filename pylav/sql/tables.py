from __future__ import annotations

import getpass
import os

from piccolo.columns import JSONB, BigInt, Boolean, Float, Integer, Text, Timestamptz
from piccolo.engine import PostgresEngine
from piccolo.table import Table

if getpass.getuser() == "draper":  # FIXME: This is a hack im lazy and should be removed before release
    DATABASE = "py_lav"
    USER = "draper"
    PASSWORD = "testing"  # noqa
    PORT = "5433"
else:
    PORT = os.getenv("PYLAV__POSTGRES_POST", "5432")
    PASSWORD = os.getenv("PYLAV__POSTGRES_PASSWORD", "")
    USER = os.getenv("PYLAV__POSTGRES_USER", "postgres")
    DATABASE = os.getenv("PYLAV__POSTGRES_DB", "pylav")
HOST = os.getenv("PYLAV__POSTGRES_HOST", "localhost")


DB = PostgresEngine(config={"host": HOST, "port": int(PORT), "database": DATABASE, "user": USER, "password": PASSWORD})


class PlaylistRow(Table, db=DB, tablename="playlist"):
    id = BigInt(primary_key=True)
    scope = BigInt(null=False, index=True)
    author = BigInt(null=False, index=True)
    name = Text(null=False, index=True)
    url = Text(null=True)
    tracks = JSONB(null=False, default=[])


class LibConfigRow(Table, db=DB, tablename="lib_config"):
    bot = BigInt(primary_key=True, index=True)
    id = BigInt(index=True)
    config_folder = Text(null=False)
    localtrack_folder = Text(null=True)
    java_path = Text(null=False, default="java")
    enable_managed_node = Boolean(null=False, default=True)
    auto_update_managed_nodes = Boolean(null=False, default=True)
    extras: JSONB = JSONB(null=False, default={})


class EqualizerRow(Table, db=DB, tablename="equalizer"):
    id = BigInt(primary_key=True, index=True)
    scope = BigInt(null=False, index=True)
    name = Text(null=True, index=True)
    description = Text(null=True)
    author = BigInt(null=False, index=True)
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
    id = BigInt(primary_key=True, index=True)
    bot = BigInt(index=True, null=False)
    channel_id = BigInt(null=False)
    volume = Integer(null=False, default=100)
    position = Float(null=False, default=0.0)
    auto_play_playlist_id = BigInt(null=True)
    text_channel_id = BigInt(null=True)
    notify_channel_id = BigInt(null=True)

    paused = Boolean(null=False, default=False)
    repeat_current = Boolean(null=False, default=False)
    repeat_queue = Boolean(null=False, default=False)
    shuffle = Boolean(null=False, default=False)
    auto_play = Boolean(null=False, default=False)
    playing = Boolean(null=False, default=False)
    effect_enabled = Boolean(null=False, default=False)
    self_deaf = Boolean(null=False, default=False)

    current = JSONB(null=True)
    queue = JSONB(null=False, default=[])
    history = JSONB(null=False, default=[])
    effects = JSONB(null=False, default={})
    extras = JSONB(null=False, default={})


class PlayerRow(Table, db=DB, tablename="player"):
    id = BigInt(primary_key=True, index=True)
    bot = BigInt(index=True, null=False)
    volume = Integer(null=False, default=100)
    auto_play_playlist_id = BigInt(null=False, default=1)

    text_channel_id = BigInt(null=True)
    notify_channel_id = BigInt(null=True)
    forced_channel_id = BigInt(null=True)

    repeat_current = Boolean(null=False, default=False)
    repeat_queue = Boolean(null=False, default=False)
    shuffle = Boolean(null=False, default=False)
    auto_play = Boolean(null=False, default=True)
    self_deaf = Boolean(null=False, default=True)
    extras = JSONB(null=False, default={})


class NodeRow(Table, db=DB, tablename="node"):
    id = BigInt(primary_key=True, index=True)
    name = Text(null=False)
    ssl = Boolean(null=False, default=False)
    resume_key = Text(null=True)
    resume_timeout = Integer(null=False, default=600)
    reconnect_attempts = Integer(null=False)
    search_only = Boolean(null=False, default=False)
    managed = Boolean(null=False, default=False)
    disabled_sources = JSONB(null=False, default=[])
    extras = JSONB(null=True)
    yaml = JSONB(null=True)


class QueryRow(Table, db=DB, tablename="query"):
    identifier = Text(null=False, index=True, primary_key=True)
    name = Text(null=True)
    tracks = JSONB(null=False, default=[])
    last_updated = Timestamptz(null=False, index=True)


class BotVersionRow(Table, db=DB, tablename="version"):
    bot = BigInt(primary_key=True, index=True)
    version = Text(null=False)
