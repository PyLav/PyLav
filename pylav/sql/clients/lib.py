from __future__ import annotations

from typing import TYPE_CHECKING

from pylav._config import CONFIG_DIR
from pylav._logging import getLogger
from pylav.sql import tables
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
        await tables.PlaylistRow.create_table(if_not_exists=True)
        await tables.LibConfigRow.create_table(if_not_exists=True)
        await tables.LibConfigRow.create_index(
            columns=[tables.LibConfigRow.bot, tables.LibConfigRow.id], if_not_exists=True
        )

        await tables.EqualizerRow.create_table(if_not_exists=True)
        await tables.PlayerStateRow.create_table(if_not_exists=True)
        await tables.PlayerStateRow.create_index(
            columns=[tables.PlayerStateRow.bot, tables.PlayerStateRow.id], if_not_exists=True
        )

        await tables.PlayerRow.create_table(if_not_exists=True)
        await tables.PlayerRow.create_index(columns=[tables.PlayerRow.bot, tables.PlayerRow.id], if_not_exists=True)

        await tables.PlayerRow.raw(array_remove_script)
        await tables.NodeRow.create_table(if_not_exists=True)
        await tables.NodeRow.raw(array_remove_script)
        await tables.QueryRow.create_table(if_not_exists=True)
        await tables.BotVersionRow.create_table(if_not_exists=True)
        await tables.AioHttpCacheRow.create_table(if_not_exists=True)

    async def reset_database(self) -> None:
        await tables.PlaylistRow.raw(
            f"DROP TABLE "
            f"{tables.PlaylistRow._meta.tablename}, "
            f"{tables.LibConfigRow._meta.tablename}, "
            f"{tables.EqualizerRow._meta.tablename}, "
            f"{tables.PlayerStateRow._meta.tablename}, "
            f"{tables.PlayerRow._meta.tablename}, "
            f"{tables.NodeRow._meta.tablename}, "
            f"{tables.QueryRow._meta.tablename}, "
            f"{tables.BotVersionRow._meta.tablename}, "
            f"{tables.AioHttpCacheRow._meta.tablename};"
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
