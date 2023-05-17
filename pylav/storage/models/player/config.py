from __future__ import annotations

import typing
from dataclasses import dataclass

import discord
from piccolo.querystring import QueryString

from pylav.compat import json
from pylav.helpers.misc import TimedFeature
from pylav.helpers.singleton import SingletonCachedByKey
from pylav.storage.database.cache.decodators import maybe_cached
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.players import PlayerRow
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
        data = {
            "enabled": False,
            "time": 60,
        }
        await PlayerRow.insert(
            PlayerRow(
                id=0,
                bot=bot,
                volume=1000,
                max_volume=1000,
                shuffle=True,
                auto_shuffle=True,
                auto_play=True,
                self_deaf=True,
                empty_queue_dc=data,
                alone_dc=data,
                alone_pause=data,
            )
        ).on_conflict(action="DO NOTHING", target=(PlayerRow.id, PlayerRow.bot))

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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, volume=volume)).on_conflict(
            action="DO UPDATE", target=(PlayerRow.id, PlayerRow.bot), values=[PlayerRow.volume]
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, max_volume=max_volume)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.max_volume],
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
        await PlayerRow.insert(
            PlayerRow(id=self.id, bot=self.bot, auto_play_playlist_id=auto_play_playlist_id)
        ).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.auto_play_playlist_id],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, text_channel_id=text_channel_id)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.text_channel_id],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, notify_channel_id=notify_channel_id)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.notify_channel_id],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, forced_channel_id=forced_channel_id)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.forced_channel_id],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, repeat_current=repeat_current)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.repeat_current],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, repeat_queue=repeat_queue)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.repeat_queue],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, shuffle=shuffle)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.shuffle],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, auto_shuffle=auto_shuffle)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.auto_shuffle],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, auto_play=auto_play)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.auto_play],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, self_deaf=self_deaf)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.self_deaf],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, extras=extras)).on_conflict(
            action="DO UPDATE", target=(PlayerRow.id, PlayerRow.bot), values=[PlayerRow.extras]
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, effects=effects)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.effects],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, empty_queue_dc=empty_queue_dc)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.empty_queue_dc],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, alone_dc=alone_dc)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.alone_dc],
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
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, alone_pause=alone_pause)).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.alone_pause],
        )
        await self.update_cache((self.fetch_alone_pause, TimedFeature.from_dict(alone_pause)), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_dj_users(self) -> set[int]:
        """Fetch the disc jockey users of the player"""
        player = (
            await PlayerRow.select(PlayerRow.dj_users)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )

        return set(player["dj_users"] if player else PlayerRow.dj_users.default)

    async def add_to_dj_users(self, user: discord.Member) -> None:
        """Add a user to the disc jockey users of the player"""
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, dj_users=[user.id])).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.dj_users, QueryString("array_cat(player.dj_users, EXCLUDED.dj_users)")],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_users)

    async def remove_from_dj_users(self, user: discord.Member) -> None:
        """Remove a user from the disc jockey users of the player"""
        await PlayerRow.update(dj_users=QueryString("array_remove(dj_users, {})", user.id)).where(
            PlayerRow.id == self.id & PlayerRow.bot == self.bot
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_users)

    async def bulk_add_dj_users(self, *users: discord.Member) -> None:
        """Add disc jockey users to the player"""
        if not users:
            return
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, dj_users=[u.id for u in users])).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.dj_users, QueryString("array_cat(player.dj_users, EXCLUDED.dj_users)")],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_users)

    async def bulk_remove_dj_users(self, *users: discord.Member) -> None:
        """Remove disc jockey users from the player.

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
        """Reset the disc jockey users of the player"""
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, dj_users=[])).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.dj_users],
        )
        await self.update_cache((self.fetch_dj_users, set()), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_dj_roles(self) -> set[int]:
        """Fetch the disc jockey roles of the player"""
        player = (
            await PlayerRow.select(PlayerRow.dj_roles)
            .where((PlayerRow.id == self.id) & (PlayerRow.bot == self.bot))
            .first()
            .output(load_json=True, nested=True)
        )

        return set(player["dj_roles"] if player else PlayerRow.dj_roles.default)

    async def add_to_dj_roles(self, role: discord.Role) -> None:
        """Add disc jockey roles to the player"""
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, dj_roles=[role.id])).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.dj_roles, QueryString("array_cat(player.dj_roles, EXCLUDED.dj_roles)")],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_roles)

    async def remove_from_dj_roles(self, role: discord.Role) -> None:
        """Remove disc jockey roles from the player"""
        await PlayerRow.update(dj_roles=QueryString("array_remove(dj_roles, {})", role.id)).where(
            PlayerRow.id == self.id & PlayerRow.bot == self.bot
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_roles)

    async def bulk_add_dj_roles(self, *roles: discord.Role) -> None:
        """Add disc jockey roles to the player.

        Parameters
        ----------
        roles : discord.Role
            The roles to add
        """
        if not roles:
            return
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, dj_roles=[r.id for r in roles])).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.dj_roles, QueryString("array_cat(player.dj_roles, EXCLUDED.dj_roles)")],
        )
        await self.update_cache((self.exists, True))
        await self.invalidate_cache(self.fetch_all, self.fetch_dj_roles)

    async def bulk_remove_dj_roles(self, *roles: discord.Role) -> None:
        """Remove disc jockey roles from the player.

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
        """Reset the disc jockey roles of the player"""
        await PlayerRow.insert(PlayerRow(id=self.id, bot=self.bot, dj_roles=[])).on_conflict(
            action="DO UPDATE",
            target=(PlayerRow.id, PlayerRow.bot),
            values=[PlayerRow.dj_roles],
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
    ) -> bool:
        """Check if a user is a disc jockey.

        Parameters
        ----------
        user : discord.Member
            The user to check.
        additional_role_ids : list
            The additional disc jockey role ids to check.
        additional_user_ids : list
            The additional disc jockey user ids to check.

        Returns
        -------
        bool
            Whether the user is a disc jockey.
        """
        if additional_user_ids and user.id in additional_user_ids:
            return True
        if additional_role_ids and any(r.id in additional_role_ids for r in user.roles):
            return True
        if __ := user.guild:
            bot = self.client.bot
            if hasattr(bot, "is_owner") and await bot.is_owner(typing.cast(discord.User, user)):
                return True
            if hasattr(bot, "is_admin") and await bot.is_admin(user):
                return True
            if hasattr(bot, "is_mod") and await bot.is_mod(user):
                return True
        if await self._userid_in_dj_users(user.id):
            return True
        dj_roles = await self.fetch_dj_roles()
        return any(r.id in dj_roles for r in user.roles) if dj_roles else True
