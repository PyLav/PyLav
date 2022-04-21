from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

import aiopath
from piccolo.table import create_tables

from pylav._config import CONFIG_DIR
from pylav.sql.models import LibConfigModel
from pylav.sql.tables import LibConfigRow, NodeRow, PlayerRow, PlaylistRow, QueryRow

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("red.PyLink.LibConfigManager")


class LibConfigManager:
    def __init__(self, client: Client):
        __database_folder: aiopath.AsyncPath = CONFIG_DIR
        __default_db_name: aiopath.AsyncPath = __database_folder / "config.db"
        self._client = client
        self._config_folder = CONFIG_DIR
        self._entry = LibConfigModel(1)

    async def initialize(self) -> None:
        await self.create_tables()

    @property
    def client(self) -> Client:
        return self._client

    async def create_tables(self) -> None:
        create_tables(PlaylistRow, LibConfigRow, PlayerRow, NodeRow, QueryRow, if_not_exists=True)

    @staticmethod
    async def get_config(config_folder, java_path, enable_managed_node, auto_update_managed_nodes) -> LibConfigModel:
        return await LibConfigModel.get_or_create(
            id=1,
            config_folder=f"{config_folder}",
            java_path=java_path,
            enable_managed_node=enable_managed_node,
            auto_update_managed_nodes=auto_update_managed_nodes,
        )

    async def set_lib_config(
        self,
        config_folder: aiopath.AsyncPath | str,
        java_path: str,
        enable_managed_node: bool,
        auto_update_managed_nodes: bool,
    ) -> LibConfigModel:
        config_folder: aiopath.AsyncPath = aiopath.AsyncPath(config_folder)
        if await config_folder.is_file():
            raise ValueError("The config folder must be a directory.")
        if await config_folder.is_dir() and not await config_folder.exists():
            await config_folder.mkdir(parents=True, exist_ok=True)

        self._config_folder = config_folder
        return await LibConfigModel(
            id=1,
            config_folder=str(config_folder),
            java_path=java_path,
            enable_managed_node=enable_managed_node,
            auto_update_managed_nodes=auto_update_managed_nodes,
        ).save()
