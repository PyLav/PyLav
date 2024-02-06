from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pylav.logging import getLogger
from pylav.storage.migrations.high_level.always.fix_managed_node_settings import fix_managed_node_settings
from pylav.storage.migrations.high_level.always.process_envvar_variables import process_envvar_variables
from pylav.storage.migrations.high_level.always.set_pylav_version import set_current_version
from pylav.storage.migrations.high_level.always.set_ram_value import set_correct_ram_cap
from pylav.storage.migrations.high_level.always.update_managed_node_settings import update_managed_node_settings
from pylav.storage.migrations.high_level.one_offs.v0_0_0_2 import migration_v_0_0_0_2
from pylav.storage.migrations.high_level.one_offs.v0_3_2_0 import migration_v_0_3_2_0
from pylav.storage.migrations.high_level.one_offs.v0_3_3_0 import migration_v_0_3_3_0
from pylav.storage.migrations.high_level.one_offs.v0_3_4_0 import migration_v_0_3_4_0
from pylav.storage.migrations.high_level.one_offs.v0_3_5_0 import migration_v_0_3_5_0
from pylav.storage.migrations.high_level.one_offs.v0_3_6_0 import migration_v_0_3_6_0
from pylav.storage.migrations.high_level.one_offs.v0_7_6_0 import migration_v_0_7_6_0
from pylav.storage.migrations.high_level.one_offs.v0_8_5_0 import migration_v_0_8_5_0
from pylav.storage.migrations.high_level.one_offs.v0_8_8_0 import migration_v_0_8_8_0
from pylav.storage.migrations.high_level.one_offs.v0_9_2_0 import migration_v_0_9_2_0
from pylav.storage.migrations.high_level.one_offs.v0_10_5_0 import migration_v_0_10_5_0
from pylav.storage.migrations.high_level.one_offs.v0_11_3_0 import migration_v_0_11_3_0
from pylav.storage.migrations.high_level.one_offs.v0_11_8_0 import migration_v_0_11_8_0
from pylav.storage.migrations.high_level.one_offs.v1_0_0 import migration_v_1_0_0
from pylav.storage.migrations.high_level.one_offs.v1_0_17 import migration_v_1_1_17
from pylav.storage.migrations.high_level.one_offs.v1_10_0 import migration_v_1_10_0
from pylav.storage.migrations.high_level.one_offs.v1_10_1 import migration_v_1_10_1
from pylav.storage.migrations.high_level.one_offs.v1_12_0 import migration_v_1_12_0
from pylav.storage.migrations.high_level.one_offs.v1_14_0 import migration_v_1_14_0

if TYPE_CHECKING:
    from pylav.core.client import Client
LOGGER = getLogger("PyLav.Database.Controller.Migration")


class MigrationController:
    __slots__ = ("_client", "_tasks_depend_on_node")

    def __init__(self, client: Client):
        self._client = client
        self._tasks_depend_on_node: list[asyncio.Task[None]] = []

    async def run_updates(self) -> None:
        """Run through schema migrations"""

        current_version = await self._client.lib_db_manager.get_bot_db_version().fetch_version()
        await fix_managed_node_settings(self._client)
        await migration_v_0_0_0_2(self._client, current_version)
        await migration_v_0_3_2_0(self._client, current_version)
        await migration_v_0_3_3_0(self._client, current_version)
        await migration_v_0_3_4_0(self._client, current_version)
        await migration_v_0_3_5_0(self._client, current_version)
        await migration_v_0_3_6_0(self._client, current_version)
        await migration_v_0_7_6_0(self._client, current_version)
        await migration_v_0_8_5_0(self._client, current_version)
        await migration_v_0_8_8_0(self._client, current_version)
        await migration_v_0_9_2_0(self._client, current_version)
        await migration_v_0_10_5_0(self._client, current_version)
        await migration_v_0_11_3_0(self._client, current_version)
        await migration_v_0_11_8_0(self._client, current_version)
        await migration_v_1_0_0(self._client, current_version)
        await migration_v_1_1_17(self._client, current_version)
        await migration_v_1_10_0(self._client, current_version)
        await migration_v_1_10_1(self._client, current_version)
        await migration_v_1_12_0(self._client, current_version)
        await migration_v_1_14_0(self._client, current_version)
        await set_current_version(self._client)
        await set_correct_ram_cap(self._client)
        await process_envvar_variables(self._client)
        await update_managed_node_settings(self._client)

    async def run_deferred_tasks_which_depend_on_node(self) -> None:
        for coro in self._tasks_depend_on_node:
            try:
                await coro
            except Exception as e:
                LOGGER.error("Error running deferred task - %s", coro.get_name(), exc_info=e)
