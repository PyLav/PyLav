from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from pylav.logging import getLogger
from pylav.storage.database.tables.player_state import PlayerStateRow
from pylav.storage.models.player.state import PlayerState
from pylav.type_hints.dict_typing import JSON_DICT_TYPE

if TYPE_CHECKING:
    from pylav.core.client import Client
LOGGER = getLogger("PyLav.Database.Controller.Player.State")


class PlayerStateController:
    __slots__ = ("_client",)

    def __init__(self, client: Client) -> None:
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    async def save_players(self, players: list[JSON_DICT_TYPE]) -> None:
        for player in players:
            await self.save_player(player)
        LOGGER.debug("Saved %s players", len(players))

    async def save_player(self, player: JSON_DICT_TYPE) -> None:
        await PlayerState(bot=self.client.bot.user.id, **player).save()
        LOGGER.trace("Saved player %s", player.get("id"))

    async def fetch_player(self, guild_id: int) -> PlayerState | None:
        return await PlayerState.get(bot_id=self._client.bot.user.id, guild_id=guild_id)

    async def fetch_all_players(self) -> AsyncIterator[PlayerState]:
        for entry in await PlayerStateRow.select(
            *(PlayerStateRow.all_columns(exclude=[PlayerStateRow.primary_key]))
        ).where(PlayerStateRow.bot == self.client.bot.user.id):
            yield PlayerState(**entry)

    async def delete_player(self, guild_id: int) -> None:
        await PlayerStateRow.delete().where(
            (PlayerStateRow.bot == self.client.bot.user.id) & (PlayerStateRow.id == guild_id)
        )

    async def delete_all_players(self) -> None:
        await PlayerStateRow.delete().where(PlayerStateRow.bot == self.client.bot.user.id)
