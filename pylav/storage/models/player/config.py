from __future__ import annotations

import typing
from dataclasses import dataclass

import asyncstdlib
import discord

from pylav.compat import json
from pylav.helpers.misc import TimedFeature
from pylav.helpers.singleton import SingletonCachedByKey
from pylav.storage.database.cache.decodators import maybe_cached
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.players import PlayerRow
from pylav.type_hints.bot import DISCORD_BOT_TYPE
from pylav.type_hints.dict_typing import JSON_DICT_TYPE


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class PlayerConfig(CachedModel, metaclass=SingletonCachedByKey):
    id: int
    bot: int

    def get_cache_key(self) -> str:
        return f"{self.id}:{self.bot}"

    @classmethod
    async def create_global(cls, bot: int) -> None:
        """Create the player in the database"""
        data = json.dumps(
            {
                "enabled": False,
                "time": 60,
            }
        )
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """
            INSERT INTO player
            (id, bot, volume,
            max_volume, shuffle, auto_shuffle,
            auto_play, self_deaf, empty_queue_dc,
            alone_dc, alone_pause)
            VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})
            ON CONFLICT (id, bot) DO NOTHING;
            ;
            """,
            0,
            bot,
            1000,
            1000,
            True,
            True,
            True,
            True,
            data,
            data,
            data,
        )

    async def delete(self) -> None:
        """Delete the player from the database"""
        await PlayerRow.delete().where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
        await self.invalidate_cache()

    @maybe_cached
    async def fetch_all(self) -> JSON_DICT_TYPE:
        """Get all players from the database"""
        data = (
            await PlayerRow.select()
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        if data:
            del data["primary_key"]
            data["empty_queue_dc"] = TimedFeature.from_dict(data["empty_queue_dc"])
            data["alone_dc"] = TimedFeature.from_dict(data["alone_dc"])
            data["alone_pause"] = TimedFeature.from_dict(data["alone_pause"])
            data["extras"] = data["extras"]
            data["effects"] = data["effects"]
            return data
        return {
            "id": self.id,
            "bot": self.bot,
            "volume": PlayerRow.volume.default,
            "max_volume": PlayerRow.max_volume.default,
            "auto_play_playlist_id": PlayerRow.auto_play_playlist_id.default,
            "text_channel_id": PlayerRow.text_channel_id.default,
            "notify_channel_id": PlayerRow.notify_channel_id.default,
            "forced_channel_id": PlayerRow.forced_channel_id.default,
            "repeat_current": PlayerRow.repeat_current.default,
            "repeat_queue": PlayerRow.repeat_queue.default,
            "shuffle": PlayerRow.shuffle.default,
            "auto_shuffle": PlayerRow.auto_shuffle.default,
            "auto_play": PlayerRow.auto_play.default,
            "self_deaf": PlayerRow.self_deaf.default,
            "empty_queue_dc": TimedFeature.from_dict(json.loads(PlayerRow.empty_queue_dc.default)),
            "alone_dc": TimedFeature.from_dict(json.loads(PlayerRow.alone_dc.default)),
            "alone_pause": TimedFeature.from_dict(json.loads(PlayerRow.alone_pause.default)),
            "extras": json.loads(PlayerRow.extras.default),
            "effects": json.loads(PlayerRow.effects.default),
            "dj_users": PlayerRow.dj_users.default,
            "dj_roles": PlayerRow.dj_roles.default,
        }

    @maybe_cached
    async def exists(self) -> bool:
        """Check if the player exists in the database"""
        return await PlayerRow.exists().where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))

    @maybe_cached
    async def fetch_volume(self) -> int:
        """Fetch the volume of the player from the db"""

        player = (
            await PlayerRow.select(PlayerRow.volume)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["volume"] if player else PlayerRow.volume.default

    async def update_volume(self, volume: int) -> None:
        """Update the volume of the player in the db"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, volume)
        VALUES ({}, {}, {})
        ON CONFLICT (id, bot)
         DO UPDATE SET volume = excluded.volume;""",
            self.id,
            self.bot,
            volume,
        )
        await self.update_cache((self.fetch_volume, volume), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_max_volume(self) -> int:
        """Fetch the max volume of the player from the db"""
        player = (
            await PlayerRow.select(PlayerRow.max_volume)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["max_volume"] if player else PlayerRow.max_volume.default

    async def update_max_volume(self, max_volume: int) -> None:
        """Update the max volume of the player in the db"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, max_volume)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET max_volume = excluded.max_volume;""",
            self.id,
            self.bot,
            max_volume,
        )
        await self.update_cache((self.fetch_max_volume, max_volume), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_auto_play_playlist_id(self) -> int:
        """Fetch the auto play playlist ID of the player"""
        player = (
            await PlayerRow.select(PlayerRow.auto_play_playlist_id)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["auto_play_playlist_id"] if player else PlayerRow.auto_play_playlist_id.default

    async def update_auto_play_playlist_id(self, auto_play_playlist_id: int) -> None:
        """Update the auto play playlist ID of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, auto_play_playlist_id)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET auto_play_playlist_id = excluded.auto_play_playlist_id;""",
            self.id,
            self.bot,
            auto_play_playlist_id,
        )
        await self.update_cache((self.fetch_auto_play_playlist_id, auto_play_playlist_id), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_text_channel_id(self) -> int:
        """Fetch the text channel ID of the player"""
        player = (
            await PlayerRow.select(PlayerRow.text_channel_id)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["text_channel_id"] if player else PlayerRow.text_channel_id.default

    async def update_text_channel_id(self, text_channel_id: int) -> None:
        """Update the text channel ID of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, text_channel_id)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET text_channel_id = excluded.text_channel_id;""",
            self.id,
            self.bot,
            text_channel_id,
        )
        await self.update_cache((self.fetch_text_channel_id, text_channel_id), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_notify_channel_id(self) -> int:
        """Fetch the notify channel ID of the player"""
        player = (
            await PlayerRow.select(PlayerRow.notify_channel_id)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["notify_channel_id"] if player else PlayerRow.notify_channel_id.default

    async def update_notify_channel_id(self, notify_channel_id: int) -> None:
        """Update the notify channel ID of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, notify_channel_id)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET notify_channel_id = excluded.notify_channel_id;""",
            self.id,
            self.bot,
            notify_channel_id,
        )
        await self.update_cache((self.fetch_notify_channel_id, notify_channel_id), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_forced_channel_id(self) -> int:
        """Fetch the forced channel ID of the player"""
        player = (
            await PlayerRow.select(PlayerRow.forced_channel_id)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["forced_channel_id"] if player else PlayerRow.forced_channel_id.default

    async def update_forced_channel_id(self, forced_channel_id: int) -> None:
        """Update the forced channel ID of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, forced_channel_id)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET forced_channel_id = excluded.forced_channel_id;""",
            self.id,
            self.bot,
            forced_channel_id,
        )
        await self.update_cache((self.fetch_forced_channel_id, forced_channel_id), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_repeat_current(self) -> bool:
        """Fetch the repeat current of the player"""
        player = (
            await PlayerRow.select(PlayerRow.repeat_current)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["repeat_current"] if player else PlayerRow.repeat_current.default

    async def update_repeat_current(self, repeat_current: bool) -> None:
        """Update the repeat current of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, repeat_current)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET repeat_current = excluded.repeat_current;""",
            self.id,
            self.bot,
            repeat_current,
        )
        await self.update_cache((self.fetch_repeat_current, repeat_current), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_repeat_queue(self) -> bool:
        """Fetch the repeat queue of the player"""
        player = (
            await PlayerRow.select(PlayerRow.repeat_queue)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["repeat_queue"] if player else PlayerRow.repeat_queue.default

    async def update_repeat_queue(self, repeat_queue: bool) -> None:
        """Update the repeat queue of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, repeat_queue)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET repeat_queue = excluded.repeat_queue;""",
            self.id,
            self.bot,
            repeat_queue,
        )
        await self.update_cache((self.fetch_repeat_queue, repeat_queue), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_shuffle(self) -> bool:
        """Fetch the shuffle of the player"""
        player = (
            await PlayerRow.select(PlayerRow.shuffle)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["shuffle"] if player else PlayerRow.shuffle.default

    async def update_shuffle(self, shuffle: bool) -> None:
        """Update the shuffle of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, shuffle)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET shuffle = excluded.shuffle;""",
            self.id,
            self.bot,
            shuffle,
        )
        await self.update_cache((self.fetch_shuffle, shuffle), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_auto_shuffle(self) -> bool:
        """Fetch the auto shuffle of the player"""
        player = (
            await PlayerRow.select(PlayerRow.auto_shuffle)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["auto_shuffle"] if player else PlayerRow.auto_shuffle.default

    async def update_auto_shuffle(self, auto_shuffle: bool) -> None:
        """Update the auto shuffle of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, auto_shuffle)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET auto_shuffle = excluded.auto_shuffle;""",
            self.id,
            self.bot,
            auto_shuffle,
        )
        await self.update_cache((self.fetch_auto_shuffle, auto_shuffle), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_auto_play(self) -> bool:
        """Fetch the auto play of the player"""
        player = (
            await PlayerRow.select(PlayerRow.auto_play)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["auto_play"] if player else PlayerRow.auto_play.default

    async def update_auto_play(self, auto_play: bool) -> None:
        """Update the auto play of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, auto_play)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET auto_play = excluded.auto_play;""",
            self.id,
            self.bot,
            auto_play,
        )
        await self.update_cache((self.fetch_auto_play, auto_play), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_self_deaf(self) -> bool:
        """Fetch the self deaf of the player"""
        player = (
            await PlayerRow.select(PlayerRow.self_deaf)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["self_deaf"] if player else PlayerRow.self_deaf.default

    async def update_self_deaf(self, self_deaf: bool) -> None:
        """Update the self deaf of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, self_deaf)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET self_deaf = excluded.self_deaf;""",
            self.id,
            self.bot,
            self_deaf,
        )
        await self.update_cache((self.fetch_self_deaf, self_deaf), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_extras(self) -> JSON_DICT_TYPE:
        """Fetch the extras of the player"""
        player = (
            await PlayerRow.select(PlayerRow.extras)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["extras"] if player else json.loads(PlayerRow.extras.default)

    async def update_extras(self, extras: JSON_DICT_TYPE) -> None:
        """Update the extras of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, extras)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET extras = excluded.extras;""",
            self.id,
            self.bot,
            json.dumps(extras),
        )
        await self.update_cache((self.fetch_extras, extras), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_effects(
        self,
    ) -> dict[str, int | None | dict[str, int | float | list[dict[str, float | None]] | None]]:
        """Fetch the effects of the player"""
        player = (
            await PlayerRow.select(PlayerRow.effects)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return player["effects"] if player else json.loads(PlayerRow.effects.default)

    async def update_effects(
        self, effects: dict[str, int | None | dict[str, int | float | list[dict[str, float | None]] | None]]
    ) -> None:
        """Update the effects of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, effects)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET effects = excluded.effects;""",
            self.id,
            self.bot,
            json.dumps(effects),
        )
        await self.update_cache((self.fetch_effects, effects), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_empty_queue_dc(self) -> TimedFeature:
        """Fetch the empty queue dc of the player"""
        player = (
            await PlayerRow.select(PlayerRow.empty_queue_dc)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return TimedFeature.from_dict(
            player["empty_queue_dc"] if player else json.loads(PlayerRow.empty_queue_dc.default)
        )

    async def update_empty_queue_dc(self, empty_queue_dc: dict[str, int | bool]) -> None:
        """Update the empty queue dc of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, empty_queue_dc)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET empty_queue_dc = excluded.empty_queue_dc;""",
            self.id,
            self.bot,
            json.dumps(empty_queue_dc),
        )
        await self.update_cache(
            (self.fetch_empty_queue_dc, TimedFeature.from_dict(empty_queue_dc)), (self.exists, True)
        )
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_alone_dc(self) -> TimedFeature:
        """Fetch the alone dc of the player"""
        player = (
            await PlayerRow.select(PlayerRow.alone_dc)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return TimedFeature.from_dict(player["alone_dc"] if player else json.loads(PlayerRow.alone_dc.default))

    async def update_alone_dc(self, alone_dc: dict[str, int | bool]) -> None:
        """Update the alone dc of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, alone_dc)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET alone_dc = excluded.alone_dc;""",
            self.id,
            self.bot,
            json.dumps(alone_dc),
        )
        await self.update_cache((self.fetch_alone_dc, TimedFeature.from_dict(alone_dc)), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_alone_pause(self) -> TimedFeature:
        """Fetch the alone pause of the player"""
        player = (
            await PlayerRow.select(PlayerRow.alone_pause)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )
        return TimedFeature.from_dict(player["alone_pause"] if player else json.loads(PlayerRow.alone_pause.default))

    async def update_alone_pause(self, alone_pause: dict[str, int | bool]) -> None:
        """Update the alone pause of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, alone_pause)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET alone_pause = excluded.alone_pause;""",
            self.id,
            self.bot,
            json.dumps(alone_pause),
        )
        await self.update_cache((self.fetch_alone_pause, TimedFeature.from_dict(alone_pause)), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_dj_users(self) -> set[int]:
        """Fetch the dj users of the player"""
        player = (
            await PlayerRow.select(PlayerRow.dj_users)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )

        return set(player["dj_users"] if player else PlayerRow.dj_users.default)

    async def add_to_dj_users(self, user: discord.Member) -> None:
        """Add a user to the dj users of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, dj_users)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET dj_users = array_cat(player.dj_users, EXCLUDED.dj_users);""",
            self.id,
            self.bot,
            [user.id],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_users)

    async def remove_from_dj_users(self, user: discord.Member) -> None:
        """Remove a user from the dj users of the player"""
        # TODO: When piccolo add more functions for dealing with arrays update this to become ORM
        await PlayerRow.raw(
            "UPDATE player SET dj_users = array_remove(dj_users, {}) WHERE id = {} AND bot = {};",
            user.id,
            self.id,
            self.bot,
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_users)

    async def bulk_add_dj_users(self, *users: discord.Member) -> None:
        """Add dj users to the player"""
        if not users:
            return
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, dj_users)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET dj_users = array_cat(player.dj_users, EXCLUDED.dj_users);""",
            self.id,
            self.bot,
            [u.id for u in users],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_users)

    async def bulk_remove_dj_users(self, *users: discord.Member) -> None:
        """Remove dj users from the player.

        Parameters
        ----------
        users : discord.Member
            The users to add
        """
        if not users:
            return
        for user in users:
            await self.remove_from_dj_users(user)

    async def dj_users_reset(self) -> None:
        """Reset the dj users of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """
            INSERT INTO player (id, bot, dj_users) VALUES ({}, {}, {})
            ON CONFLICT (id, bot) DO UPDATE SET dj_users = excluded.dj_users;
            """,
            self.id,
            self.bot,
            [],
        )
        await self.update_cache((self.fetch_dj_users, set()), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_dj_roles(self) -> set[int]:
        """Fetch the dj roles of the player"""
        player = (
            await PlayerRow.select(PlayerRow.dj_roles)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )

        return set(player["dj_roles"] if player else PlayerRow.dj_roles.default)

    async def add_to_dj_roles(self, role: discord.Role) -> None:
        """Add dj roles to the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, dj_roles)
            VALUES ({}, {}, {})
            ON CONFLICT (id, bot)
            DO UPDATE SET dj_roles = array_cat(player.dj_roles, EXCLUDED.dj_roles)""",
            self.id,
            self.bot,
            [role.id],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_roles)

    async def remove_from_dj_roles(self, role: discord.Role) -> None:
        """Remove dj roles from the player"""
        # TODO: When piccolo add more functions for dealing with arrays update this to become ORM

        await PlayerRow.raw(
            """UPDATE player SET dj_roles = array_remove(dj_roles, {}) WHERE id = {} AND bot = {}""",
            role.id,
            self.id,
            self.bot,
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_roles)

    async def bulk_add_dj_roles(self, *roles: discord.Role) -> None:
        """Add dj roles to the player.

        Parameters
        ----------
        roles : discord.Role
            The roles to add"
        """
        if not roles:
            return
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """INSERT INTO player (id, bot, dj_roles)
                    VALUES ({}, {}, {})
                    ON CONFLICT (id, bot)
                    DO UPDATE SET dj_roles = array_cat(player.dj_roles, EXCLUDED.dj_roles);""",
            self.id,
            self.bot,
            [r.id for r in roles],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_roles)

    async def bulk_remove_dj_roles(self, *roles: discord.Role) -> None:
        """Remove dj roles from the player.

        Parameters
        ----------
        roles : discord.Role
            The roles to add.
        """
        if not roles:
            return
        for role in roles:
            await self.remove_from_dj_roles(role)

    async def dj_roles_reset(self) -> None:
        """Reset the dj roles of the player"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await PlayerRow.raw(
            """
                    INSERT INTO player (id, bot, dj_roles) VALUES ({}, {}, {})
                    ON CONFLICT (id, bot) DO UPDATE SET dj_roles = excluded.dj_roles;
                    """,
            self.id,
            self.bot,
            [],
        )
        await self.update_cache((self.fetch_dj_roles, set()), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    async def _role_id_in_dj_roles(self, role_id: int) -> bool:
        return await PlayerRow.exists().where(
            (PlayerRow.id == self.id) & (PlayerRow.bot == self.bot) & PlayerRow.dj_roles.any(role_id)
        )

    async def _userid_in_dj_users(self, user_id: int) -> bool:
        return await PlayerRow.exists().where(
            (PlayerRow.id == self.id) & (PlayerRow.bot == self.bot) & PlayerRow.dj_users.any(user_id)
        )

    async def is_dj(
        self,
        user: discord.Member,
        *,
        additional_role_ids: list | None = None,
        additional_user_ids: list | None = None,
        bot: DISCORD_BOT_TYPE = None,
    ) -> bool:
        """Check if a user is a dj.

        Parameters
        ----------
        user : discord.Member
            The user to check.
        additional_role_ids : list
            The additional dj role ids to check.
        additional_user_ids : list
            The additional dj user ids to check.
        bot : DISCORD_BOT_TYPE
            The bot instance to check for owners, admins or mods.

        Returns
        -------
        bool
            Whether the user is a dj.
        """
        if additional_user_ids and user.id in additional_user_ids:
            return True
        if additional_role_ids and await asyncstdlib.any(r.id in additional_role_ids for r in user.roles):
            return True
        if __ := user.guild:
            if hasattr(bot, "is_owner") and await bot.is_owner(typing.cast(discord.User, user)):
                return True
            if hasattr(bot, "is_admin") and await bot.is_admin(user):
                return True
            if hasattr(bot, "is_mod") and await bot.is_mod(user):
                return True
        if await self._userid_in_dj_users(user.id):
            return True
        dj_roles = await self.fetch_dj_roles()
        return bool(await asyncstdlib.any(r.id in dj_roles for r in user.roles)) if dj_roles else True
