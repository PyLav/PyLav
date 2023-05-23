from __future__ import annotations

from piccolo.columns import JSONB, UUID, Array, BigInt, Boolean, Integer
from piccolo.table import Table

from pylav.constants.config import DEFAULT_PLAYER_VOLUME
from pylav.storage.database.tables.misc import DATABASE_ENGINE


class PlayerRow(Table, db=DATABASE_ENGINE, tablename="player"):
    primary_key = UUID(primary_key=True)
    id = BigInt(index=True)
    bot = BigInt(index=True, null=False)
    volume = Integer(null=False, default=DEFAULT_PLAYER_VOLUME)
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
