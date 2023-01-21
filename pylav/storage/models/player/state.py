from __future__ import annotations

from dataclasses import dataclass

from pylav.compat import json
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.player_state import PlayerStateRow
from pylav.type_hints.dict_typing import JSON_DICT_TYPE


@dataclass(eq=True)
class PlayerState(CachedModel):
    id: int
    bot: int
    channel_id: int
    volume: int
    position: float
    auto_play_playlist_id: int | None
    text_channel_id: int | None
    notify_channel_id: int | None
    forced_channel_id: int | None

    paused: bool
    repeat_current: bool
    repeat_queue: bool
    shuffle: bool
    auto_shuffle: bool
    auto_play: bool
    playing: bool
    effect_enabled: bool
    self_deaf: bool

    current: JSON_DICT_TYPE | None
    queue: list[JSON_DICT_TYPE]
    history: list[JSON_DICT_TYPE]
    effects: JSON_DICT_TYPE
    extras: JSON_DICT_TYPE
    pk: None = None

    def get_cache_key(self) -> str:
        return f"{self.id}:{self.bot}:{self.channel_id}"

    def __post_init__(self) -> None:
        if isinstance(self.current, str):
            self.current = json.loads(self.current)
        if isinstance(self.queue, str):
            self.queue = json.loads(self.queue)
        if isinstance(self.history, str):
            self.history = json.loads(self.history)
        if isinstance(self.effects, str):
            self.effects = json.loads(self.effects)
        if isinstance(self.extras, str):
            self.extras = json.loads(self.extras)

    async def delete(self) -> None:
        """Delete the player state from the database"""
        await PlayerStateRow.delete().where((PlayerStateRow.id == self.id) & (PlayerStateRow.bot == self.bot))

    async def save(self) -> None:
        """Save the player state to the database"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerStateRow.raw(
            """
            INSERT INTO player_state (
                id,
                bot,
                channel_id,
                volume,
                position,
                auto_play_playlist_id,
                forced_channel_id,
                text_channel_id,
                notify_channel_id,
                paused,
                repeat_current,
                repeat_queue,
                shuffle,
                auto_shuffle,
                auto_play,
                playing,
                effect_enabled,
                self_deaf,
                current,
                queue,
                history,
                effects,
                extras
            )
            VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE
                SET channel_id = excluded.channel_id,
                    volume = excluded.volume,
                    position = excluded.position,
                    auto_play_playlist_id = excluded.auto_play_playlist_id,
                    forced_channel_id = excluded.forced_channel_id,
                    text_channel_id = excluded.text_channel_id,
                    notify_channel_id = excluded.notify_channel_id,
                    paused = excluded.paused,
                    repeat_current = excluded.repeat_current,
                    repeat_queue = excluded.repeat_queue,
                    shuffle = excluded.shuffle,
                    auto_shuffle = excluded.auto_shuffle,
                    auto_play = excluded.auto_play,
                    playing = excluded.playing,
                    effect_enabled = excluded.effect_enabled,
                    self_deaf = excluded.self_deaf,
                    current = excluded.current,
                    queue = excluded.queue,
                    history = excluded.history,
                    effects = excluded.effects,
                    extras = excluded.extras;
            """,
            self.id,
            self.bot,
            self.channel_id,
            self.volume,
            self.position,
            self.auto_play_playlist_id,
            self.forced_channel_id,
            self.text_channel_id,
            self.notify_channel_id,
            self.paused,
            self.repeat_current,
            self.repeat_queue,
            self.shuffle,
            self.auto_shuffle,
            self.auto_play,
            self.playing,
            self.effect_enabled,
            self.self_deaf,
            json.dumps(self.current),
            json.dumps(self.queue),
            json.dumps(self.history),
            json.dumps(self.effects),
            json.dumps(self.extras),
        )

    @classmethod
    async def get(cls, bot_id: int, guild_id: int) -> PlayerState | None:
        """Get the player state from the database.

        Parameters
        ----------
        bot_id : int
            The bot ID.
        guild_id : int
            The guild ID.

        Returns
        -------
        PlayerState | None
            The player state if found, otherwise None.
        """
        player = (
            await PlayerStateRow.select(
                PlayerStateRow.id,
                PlayerStateRow.bot,
                PlayerStateRow.channel_id,
                PlayerStateRow.volume,
                PlayerStateRow.position,
                PlayerStateRow.auto_play_playlist_id,
                PlayerStateRow.forced_channel_id,
                PlayerStateRow.text_channel_id,
                PlayerStateRow.notify_channel_id,
                PlayerStateRow.paused,
                PlayerStateRow.repeat_current,
                PlayerStateRow.repeat_queue,
                PlayerStateRow.shuffle,
                PlayerStateRow.auto_shuffle,
                PlayerStateRow.auto_play,
                PlayerStateRow.playing,
                PlayerStateRow.effect_enabled,
                PlayerStateRow.self_deaf,
                PlayerStateRow.current,
                PlayerStateRow.queue,
                PlayerStateRow.history,
                PlayerStateRow.effects,
                PlayerStateRow.extras,
            )
            .where((PlayerStateRow.id == guild_id) & (PlayerStateRow.bot == bot_id))
            .first()
            .output(load_json=True, nested=True)
        )
        return cls(**player) if player else None
