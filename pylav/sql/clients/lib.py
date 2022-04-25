from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import aiopath
from piccolo.table import create_tables
from red_commons.logging import getLogger

from pylav._config import CONFIG_DIR
from pylav.sql.models import BotVersion, LibConfigModel
from pylav.sql.tables import BotVersionRow, LibConfigRow, NodeRow, PlayerRow, PlaylistRow, QueryRow

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("red.PyLink.LibConfigManager")


class LibConfigManager:
    def __init__(self, client: Client):
        __database_folder: aiopath.AsyncPath = CONFIG_DIR
        __default_db_name: aiopath.AsyncPath = __database_folder / "config.db"
        self._client = client
        self._config_folder = CONFIG_DIR

    async def initialize(self) -> None:
        await self.create_tables()

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    async def create_tables() -> None:
        await asyncio.to_thread(
            create_tables, PlaylistRow, LibConfigRow, PlayerRow, NodeRow, QueryRow, BotVersionRow, if_not_exists=True
        )

    async def get_config(
        self,
        config_folder,
        localtrack_folder,
        java_path,
        enable_managed_node,
        auto_update_managed_nodes,
        disabled_sources,
    ) -> LibConfigModel:
        return await LibConfigModel.get_or_create(
            id=1,
            bot=self.client.bot.user.id,
            config_folder=f"{config_folder}",
            localtrack_folder=f"{localtrack_folder}",
            java_path=java_path,
            enable_managed_node=enable_managed_node,
            auto_update_managed_nodes=auto_update_managed_nodes,
            disabled_sources=disabled_sources,
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
        bv = BotVersion(bot=self._client.bot.user.id, version="0.0.0.0")
        await bv.get_or_create()
        return bv

    async def update_bot_dv_version(self, version: str) -> None:
        bv = BotVersion(bot=self._client.bot.user.id, version=version)
        await bv.save()
