from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from pylav._logging import getLogger
from pylav.sql import tables
from pylav.sql.models import PlayerModel

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

    async def get_shuffle(self, guild_id: int) -> bool | None:
        if (await self.get_global_config()).shuffle is False:
            return False
        return (await self.get_config(guild_id)).shuffle

    async def is_dj(
        self,
        user: discord.Member,
        guild: discord.Guild,
        *,
        additional_role_ids: list = None,
        additional_user_ids: list = None,
    ) -> bool:
        if additional_user_ids and user.id in additional_user_ids:
            return True
        if additional_role_ids and any(r.id in additional_role_ids for r in user.roles):
            return True
        config = await PlayerModel(bot=self._client.bot.user.id, id=guild.id).get_or_create()
        return await config.is_dj(user=user, additional_role_ids=None, additional_user_ids=None)
