from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import Version

from pylav.constants.config import CONFIG_DIR
from pylav.storage.database.tables.aiohttp_cache import AioHttpCacheRow
from pylav.storage.database.tables.config import LibConfigRow
from pylav.storage.database.tables.equalizer import EqualizerRow
from pylav.storage.database.tables.m2m import TrackToPlaylists, TrackToQueries
from pylav.storage.database.tables.nodes import NodeRow, Sessions
from pylav.storage.database.tables.player_state import PlayerStateRow
from pylav.storage.database.tables.players import PlayerRow
from pylav.storage.database.tables.playlists import PlaylistRow
from pylav.storage.database.tables.queries import QueryRow
from pylav.storage.database.tables.tracks import TrackRow
from pylav.storage.database.tables.version import BotVersionRow
from pylav.storage.migrations.low_level.base import migrate_data, run_low_level_migrations
from pylav.storage.models.config import Config
from pylav.storage.models.version import BotVersion

if TYPE_CHECKING:
    from pylav.core.client import Client


class ConfigController:
    __slots__ = ("_client", "_config_folder")

    def __init__(self, client: Client) -> None:
        self._client = client
        self._config_folder = CONFIG_DIR

    async def initialize(self) -> None:
        data_to_migrate = await run_low_level_migrations(self)
        await self.create_tables()
        await migrate_data(data_to_migrate)

    @property
    def client(self) -> Client:
        return self._client

    # noinspection PyProtectedMember
    @staticmethod
    async def create_tables() -> None:
        await PlaylistRow.create_table(if_not_exists=True)
        await LibConfigRow.create_table(if_not_exists=True)
        await LibConfigRow.raw(
            f"CREATE UNIQUE INDEX IF NOT EXISTS unique_lib_config_bot_id "
            f"ON {LibConfigRow._meta.tablename} (bot, id)"
        )
        await EqualizerRow.create_table(if_not_exists=True)
        await PlayerStateRow.create_table(if_not_exists=True)
        await PlayerStateRow.raw(
            f"CREATE UNIQUE INDEX IF NOT EXISTS unique_player_state_bot_id "
            f"ON {PlayerStateRow._meta.tablename} (bot, id)"
        )
        await PlayerRow.create_table(if_not_exists=True)
        await PlayerRow.raw(
            f"CREATE UNIQUE INDEX IF NOT EXISTS unique_player_bot_id ON {PlayerRow._meta.tablename} (bot, id)"
        )
        await NodeRow.create_table(if_not_exists=True)
        await QueryRow.create_table(if_not_exists=True)
        await BotVersionRow.create_table(if_not_exists=True)
        await AioHttpCacheRow.create_table(if_not_exists=True)
        await TrackRow.create_table(if_not_exists=True)
        await TrackToPlaylists.create_table(if_not_exists=True)
        await TrackToQueries.create_table(if_not_exists=True)
        await Sessions.create_table(if_not_exists=True)
        await Sessions.raw(
            f"CREATE UNIQUE INDEX IF NOT EXISTS unique_node_bot_id ON {Sessions._meta.tablename} (bot, node)"
        )

    # noinspection PyProtectedMember
    async def reset_database(self) -> None:
        await PlaylistRow.raw(
            f"DROP TABLE IF EXISTS "
            f"{TrackToQueries._meta.tablename}, "
            f"{TrackToPlaylists._meta.tablename}, "
            f"{PlaylistRow._meta.tablename}, "
            f"{LibConfigRow._meta.tablename}, "
            f"{EqualizerRow._meta.tablename}, "
            f"{PlayerStateRow._meta.tablename}, "
            f"{PlayerRow._meta.tablename}, "
            f"{NodeRow._meta.tablename}, "
            f"{QueryRow._meta.tablename}, "
            f"{BotVersionRow._meta.tablename}, "
            f"{AioHttpCacheRow._meta.tablename}, "
            f"{TrackRow._meta.tablename}"
            ";"
        )
        await self.create_tables()

    def get_config(
        self,
    ) -> Config:
        return Config(id=1, bot=self.client.bot.user.id)

    def get_bot_db_version(self) -> BotVersion:
        return BotVersion(id=self._client.bot.user.id)

    async def update_bot_dv_version(self, version: str | Version) -> None:
        await self.get_bot_db_version().update_version(version)
