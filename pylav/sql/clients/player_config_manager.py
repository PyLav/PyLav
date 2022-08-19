from __future__ import annotations

from typing import TYPE_CHECKING

import asyncstdlib
import discord

from pylav._logging import getLogger
from pylav.sql import tables
from pylav.sql.models import PlayerModel
from pylav.types import BotT
from pylav.utils import TimedFeature

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("PyLav.PlayerConfigManager")


class PlayerConfigManager:
    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    async def get_global_config(self) -> PlayerModel:
        return await PlayerModel(bot=self._client.bot.user.id, id=0, volume=1000).get_or_create()

    async def get_config(self, guild_id: int) -> PlayerModel:
        return await PlayerModel(bot=self._client.bot.user.id, id=guild_id).get_or_create()

    async def reset_to_default(self, guild_id: int):
        await tables.PlayerRow.delete().where(
            (tables.PlayerRow.bot == self.client.bot.user.id) & (tables.PlayerRow.id == guild_id)
        )

    async def get_volume(self, guild_id: int) -> int:
        global_vol = (await self.get_global_config()).volume
        server_vol = (await self.get_config(guild_id)).volume
        if global_vol < server_vol:
            return global_vol
        return server_vol

    async def get_shuffle(self, guild_id: int) -> bool:
        if (await self.get_global_config()).shuffle is False:
            return False
        return (await self.get_config(guild_id)).shuffle

    async def get_auto_shuffle(self, guild_id: int) -> bool:
        if (await self.get_global_config()).auto_shuffle is False:
            return False
        return (await self.get_config(guild_id)).auto_shuffle

    async def get_self_deaf(self, guild_id: int) -> bool:
        if (await self.get_global_config()).self_deaf is True:
            return True
        return (await self.get_config(guild_id)).self_deaf

    async def get_empty_queue_dc(self, guild_id: int) -> TimedFeature:
        if (global_config := await self.get_global_config()).empty_queue_dc.enabled is True:
            return global_config.empty_queue_dc
        return (await self.get_config(guild_id)).empty_queue_dc

    async def get_alone_dc(self, guild_id: int) -> TimedFeature:
        if (global_config := await self.get_global_config()).alone_dc.enabled is True:
            return global_config.alone_dc
        return (await self.get_config(guild_id)).alone_dc

    async def get_alone_pause(self, guild_id: int) -> TimedFeature:
        if (global_config := await self.get_global_config()).alone_pause.enabled is True:
            return global_config.alone_pause
        return (await self.get_config(guild_id)).alone_pause

    async def get_auto_play(self, guild_id: int) -> bool:
        if (await self.get_global_config()).auto_play is False:
            return False
        return (await self.get_config(guild_id)).auto_play

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
        config = await PlayerModel(bot=self._client.bot.user.id, id=guild.id).get_or_create()
        return await config.is_dj(user=user, additional_role_ids=None, additional_user_ids=None, bot=bot)
