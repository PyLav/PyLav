from __future__ import annotations

from typing import TYPE_CHECKING

import pylav.sql.tables.bot
import pylav.sql.tables.cache
import pylav.sql.tables.equalizers
import pylav.sql.tables.lib_config
import pylav.sql.tables.nodes
import pylav.sql.tables.player_states
import pylav.sql.tables.players
import pylav.sql.tables.playlists
import pylav.sql.tables.queries
from pylav._config import CONFIG_DIR
from pylav._logging import getLogger
from pylav.sql.models import BotVersion, LibConfigModel

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("PyLav.LibConfigManager")


class LibConfigManager:
    __slots__ = ("_client", "_config_folder")

    def __init__(self, client: Client):
        self._client = client
        self._config_folder = CONFIG_DIR

    async def initialize(self) -> None:
        await self.create_tables()

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    async def create_tables() -> None:
        array_remove_script = """
        create or replace function array_diff(array1 anyarray, array2 anyarray)
        returns anyarray language sql immutable as $$
            select coalesce(array_agg(elem), '{}')
            from unnest(array1) elem
            where elem <> all(array2)
        $$;
        """
        await pylav.sql.tables.playlists.PlaylistRow.create_table(if_not_exists=True)
        await pylav.sql.tables.lib_config.LibConfigRow.create_table(if_not_exists=True)
        await pylav.sql.tables.lib_config.LibConfigRow.raw(
            f"CREATE UNIQUE INDEX IF NOT EXISTS unique_lib_config_bot_id ON {pylav.sql.tables.lib_config.LibConfigRow._meta.tablename} (bot, id)"
        )
        await pylav.sql.tables.equalizers.EqualizerRow.create_table(if_not_exists=True)
        await pylav.sql.tables.player_states.PlayerStateRow.create_table(if_not_exists=True)
        await pylav.sql.tables.player_states.PlayerStateRow.raw(
            f"CREATE UNIQUE INDEX IF NOT EXISTS unique_player_state_bot_id ON {pylav.sql.tables.player_states.PlayerStateRow._meta.tablename} (bot, id)"
        )
        await pylav.sql.tables.players.PlayerRow.create_table(if_not_exists=True)
        await pylav.sql.tables.players.PlayerRow.raw(
            f"CREATE UNIQUE INDEX IF NOT EXISTS unique_player_bot_id ON {pylav.sql.tables.players.PlayerRow._meta.tablename} (bot, id)"
        )
        await pylav.sql.tables.players.PlayerRow.raw(array_remove_script)
        await pylav.sql.tables.nodes.NodeRow.create_table(if_not_exists=True)
        await pylav.sql.tables.nodes.NodeRow.raw(array_remove_script)
        await pylav.sql.tables.queries.QueryRow.create_table(if_not_exists=True)
        await pylav.sql.tables.bot.BotVersionRow.create_table(if_not_exists=True)
        await pylav.sql.tables.cache.AioHttpCacheRow.create_table(if_not_exists=True)

    async def reset_database(self) -> None:
        await pylav.sql.tables.playlists.PlaylistRow.raw(
            f"DROP TABLE "
            f"{pylav.sql.tables.playlists.PlaylistRow._meta.tablename}, "
            f"{pylav.sql.tables.lib_config.LibConfigRow._meta.tablename}, "
            f"{pylav.sql.tables.equalizers.EqualizerRow._meta.tablename}, "
            f"{pylav.sql.tables.player_states.PlayerStateRow._meta.tablename}, "
            f"{pylav.sql.tables.players.PlayerRow._meta.tablename}, "
            f"{pylav.sql.tables.nodes.NodeRow._meta.tablename}, "
            f"{pylav.sql.tables.queries.QueryRow._meta.tablename}, "
            f"{pylav.sql.tables.bot.BotVersionRow._meta.tablename}, "
            f"{pylav.sql.tables.cache.AioHttpCacheRow._meta.tablename};"
        )
        await self.create_tables()

    def get_config(
        self,
    ) -> LibConfigModel:
        return LibConfigModel(id=1, bot=self.client.bot.user.id)

    def get_bot_db_version(self) -> BotVersion:
        return BotVersion(id=self._client.bot.user.id)

    async def update_bot_dv_version(self, version: str) -> None:
        await self.get_bot_db_version().update_version(version)
