from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import pylav.sql.tables.player_states
from pylav._logging import getLogger
from pylav.sql.models import PlayerStateModel

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("PyLav.PlayerStateDBManager")


class PlayerStateDBManager:
    __slots__ = ("_client",)

    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    async def save_players(self, players: list[dict]):
        await asyncio.gather(*[self.save_player(player) for player in players])
        LOGGER.debug("Saved %s players", len(players))

    async def save_player(self, player: dict):
        await PlayerStateModel(bot=self.client.bot.user.id, **player).save()
        LOGGER.trace("Saved player %s", player.get("id"))

    async def fetch_player(self, guild_id: int) -> PlayerStateModel | None:
        return await PlayerStateModel.get(bot_id=self._client.bot.user.id, guild_id=guild_id)

    async def fetch_all_players(self) -> AsyncIterator[PlayerStateModel]:
        for entry in await pylav.sql.tables.player_states.PlayerStateRow.select(
            pylav.sql.tables.player_states.PlayerStateRow.all_columns(
                exclude=[pylav.sql.tables.player_states.PlayerStateRow.primary_key]
            )
        ).where(
            pylav.sql.tables.player_states.PlayerStateRow.bot == self.client.bot.user.id
        ):  # type: ignore
            yield PlayerStateModel(**entry)

    async def delete_player(self, guild_id: int):
        await pylav.sql.tables.player_states.PlayerStateRow.delete().where(
            (pylav.sql.tables.player_states.PlayerStateRow.bot == self.client.bot.user.id)
            & (pylav.sql.tables.player_states.PlayerStateRow.id == guild_id)
        )

    async def delete_all_players(self):
        await pylav.sql.tables.player_states.PlayerStateRow.delete().where(
            pylav.sql.tables.player_states.PlayerStateRow.bot == self.client.bot.user.id
        )
