from __future__ import annotations

from typing import TYPE_CHECKING

from red_commons.logging import getLogger

from pylav.sql.models import PlayerModel
from pylav.sql.tables import PlayerRow

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("red.PyLink.PlayerConfigManager")


class PlayerConfigManager:
    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    async def get_global_config(self) -> PlayerModel:
        return await PlayerModel(bot=self._client.bot.user.id, id=0).get_or_create()

    async def get_config(self, guild_id: int) -> PlayerModel:
        return await PlayerModel(bot=self._client.bot.user.id, id=guild_id).get_or_create()

    async def reset_to_default(self, guild_id: int):
        await PlayerRow.delete().where((PlayerRow.bot == self.client.bot.user.id) & (PlayerRow.id == guild_id))

    async def get_shuffle(self, guild_id: int) -> bool:
        if (await self.get_global_config()).shuffle is False:
            return False
        return (await self.get_config(guild_id)).shuffle
