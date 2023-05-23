from __future__ import annotations

from piccolo.columns import JSONB, UUID, BigInt, Boolean, Float, Integer
from piccolo.table import Table

from pylav.constants.config import DEFAULT_PLAYER_VOLUME
from pylav.storage.database.tables.misc import DATABASE_ENGINE


class PlayerStateRow(Table, db=DATABASE_ENGINE, tablename="player_state"):
    primary_key = UUID(primary_key=True)
    id = BigInt(index=True, null=False)
    bot = BigInt(index=True, null=False)
    channel_id = BigInt(null=True, default=None)
    volume = Integer(null=False, default=DEFAULT_PLAYER_VOLUME)
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
