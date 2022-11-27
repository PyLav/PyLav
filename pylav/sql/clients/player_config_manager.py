from __future__ import annotations

from typing import TYPE_CHECKING

import asyncstdlib
import discord

from pylav._logging import getLogger
from pylav.sql.models import PlayerModel
from pylav.types import BotT
from pylav.utils import TimedFeature

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("PyLav.PlayerConfigManager")


class PlayerConfigManager:
    __slots__ = ("_client",)

    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    async def initialize_global_config(self):
        await PlayerModel.create_global(bot=self.client.bot.user.id)

    def get_global_config(self) -> PlayerModel:
        return PlayerModel(bot=self.client.bot.user.id, id=0)

    def get_config(self, guild_id: int) -> PlayerModel:
        return PlayerModel(bot=self.client.bot.user.id, id=guild_id)

    async def reset_to_default(self, guild_id: int):
        await self.get_config(guild_id=guild_id).delete()

    async def get_volume(self, guild_id: int) -> int:
        global_vol = await self.get_global_config().fetch_volume()
        server_vol = await self.get_config(guild_id=guild_id).fetch_volume()
        return global_vol if global_vol < server_vol else server_vol

    async def get_max_volume(self, guild_id: int) -> int:
        global_vol = await self.get_global_config().fetch_max_volume()
        server_vol = await self.get_config(guild_id=guild_id).fetch_max_volume()
        return global_vol if global_vol < server_vol else server_vol

    async def get_shuffle(self, guild_id: int) -> bool:
        if await self.get_global_config().fetch_shuffle() is False:
            return False
        return await self.get_config(guild_id=guild_id).fetch_shuffle()

    async def get_auto_shuffle(self, guild_id: int) -> bool:
        if await self.get_global_config().fetch_auto_shuffle() is False:
            return False
        return await self.get_config(guild_id=guild_id).fetch_auto_shuffle()

    async def get_self_deaf(self, guild_id: int) -> bool:
        if await self.get_global_config().fetch_self_deaf() is True:
            return True
        return await self.get_config(guild_id=guild_id).fetch_self_deaf()

    async def get_empty_queue_dc(self, guild_id: int) -> TimedFeature:
        if (global_empty_queue_dc := await self.get_global_config().fetch_empty_queue_dc()).enabled is True:
            return global_empty_queue_dc
        return await self.get_config(guild_id=guild_id).fetch_empty_queue_dc()

    async def get_alone_dc(self, guild_id: int) -> TimedFeature:
        if (global_alone_dc := await self.get_global_config().fetch_alone_dc()).enabled is True:
            return global_alone_dc
        return await self.get_config(guild_id=guild_id).fetch_alone_dc()

    async def get_alone_pause(self, guild_id: int) -> TimedFeature:
        if (global_alone_pause := await self.get_global_config().fetch_alone_pause()).enabled is True:
            return global_alone_pause
        return await self.get_config(guild_id=guild_id).fetch_alone_pause()

    async def get_auto_play(self, guild_id: int) -> bool:
        if await self.get_global_config().fetch_auto_play() is False:
            return False
        return await self.get_config(guild_id=guild_id).fetch_auto_play()

    async def is_dj(
        self,
        user: discord.Member,
        guild: discord.Guild,
        *,
        additional_role_ids: list = None,
        additional_user_ids: list = None,
        bot: BotT = None,
    ) -> bool:
        if additional_user_ids and user.id in additional_user_ids:
            return True
        if additional_role_ids and await asyncstdlib.any(r.id in additional_role_ids for r in user.roles):
            return True
        return await self.get_config(guild_id=guild.id).is_dj(
            user=user, additional_role_ids=None, additional_user_ids=None, bot=bot
        )
