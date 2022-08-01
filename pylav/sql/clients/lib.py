from __future__ import annotations

from typing import TYPE_CHECKING

from piccolo.table import create_db_tables

from pylav._config import CONFIG_DIR
from pylav._logging import getLogger
from pylav.sql import tables
from pylav.sql.models import BotVersion, LibConfigModel
from pylav.vendored import aiopath

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("PyLav.LibConfigManager")


class LibConfigManager:
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
        await create_db_tables(
            tables.PlaylistRow,
            tables.LibConfigRow,
            tables.PlayerStateRow,
            tables.NodeRow,
            tables.QueryRow,
            tables.BotVersionRow,
            tables.PlayerRow,
            tables.EqualizerRow,
            tables.AioHttpCacheRow,
            if_not_exists=True,
        )

    async def get_config(
        self,
        config_folder,
        localtrack_folder,
        java_path,
        enable_managed_node,
        auto_update_managed_nodes,
        use_bundled_external,
    ) -> LibConfigModel:
        return await LibConfigModel.get_or_create(
            id=1,
            bot=self.client.bot.user.id,
            config_folder=f"{config_folder}",
            localtrack_folder=f"{localtrack_folder}",
            java_path=java_path,
            enable_managed_node=enable_managed_node,
            auto_update_managed_nodes=auto_update_managed_nodes,
            use_bundled_external=use_bundled_external,
        )

    async def set_lib_config(
        self,
        config_folder: aiopath.AsyncPath | str,
        java_path: str,
        localtrack_folder: aiopath.AsyncPath | str,
        enable_managed_node: bool,
        auto_update_managed_nodes: bool,
    ) -> LibConfigModel:
        config_folder: aiopath.AsyncPath = aiopath.AsyncPath(config_folder)
        localtrack_folder: aiopath.AsyncPath = aiopath.AsyncPath(localtrack_folder)
        if await config_folder.is_file():
            raise ValueError("The config folder must be a directory.")
        if await config_folder.is_dir() and not await config_folder.exists():
            await config_folder.mkdir(parents=True, exist_ok=True)

        self._config_folder = config_folder
        return await LibConfigModel(
            id=1,
            bot=self.client.bot.user.id,
            config_folder=str(config_folder),
            java_path=java_path,
            enable_managed_node=enable_managed_node,
            auto_update_managed_nodes=auto_update_managed_nodes,
            localtrack_folder=str(localtrack_folder),
        ).save()

    async def get_bot_db_version(self) -> BotVersion:
        from pylav._config import __VERSION__

        bv = BotVersion(bot=self._client.bot.user.id, version=__VERSION__)
        await bv.get_or_create()
        return bv

    async def update_bot_dv_version(self, version: str) -> None:
        bv = BotVersion(bot=self._client.bot.user.id, version=version)
        await bv.save()
