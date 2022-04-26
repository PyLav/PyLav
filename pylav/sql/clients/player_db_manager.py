from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

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

    async def save_players(self, players: list[dict]):
        for player in players:
            p = PlayerModel(bot=self.client.bot.user.id, **player)
            await p.save()
            LOGGER.debug("Saved player %s", p)

    async def save_player(self, player: dict):
        await PlayerModel(bot=self.client.bot.user.id, **player).save()

    async def get_player(self, guild_id: int) -> PlayerModel | None:
        return await PlayerModel.get(bot_id=self._client.bot.user.id, guild_id=guild_id)

    async def get_all_players(self) -> AsyncIterator[PlayerModel]:
        for entry in await PlayerRow.select().where(PlayerRow.bot == self.client.bot.user.id):
            yield PlayerModel(**entry)

    async def delete_player(self, guild_id: int):
        await PlayerRow.delete().where((PlayerRow.bot == self.client.bot.user.id) & (PlayerRow.id == guild_id))
