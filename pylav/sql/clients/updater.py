from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pylav.config_migrations import LOGGER
from pylav.config_migrations.m0002 import run_migration_0002
from pylav.config_migrations.m0320 import run_migration_0320
from pylav.config_migrations.m0330 import run_migration_0330
from pylav.config_migrations.m0340 import run_migration_0340
from pylav.config_migrations.m0350 import run_migration_0350
from pylav.config_migrations.m0360 import run_migration_0360
from pylav.config_migrations.m0760 import run_migration_0760
from pylav.config_migrations.m0850 import run_migration_0850
from pylav.config_migrations.m0880 import run_migration_0880
from pylav.config_migrations.m0920 import run_migration_0920
from pylav.config_migrations.m01050 import run_migration_01050
from pylav.config_migrations.m01130 import run_migration_01130
from pylav.config_migrations.m01180 import run_migration_01180
from pylav.config_migrations.m010000 import run_migration_010000
from pylav.config_migrations.set_correct_ram import set_correct_ram_cap
from pylav.config_migrations.set_current_version import set_current_version

if TYPE_CHECKING:
    from pylav.client import Client


class UpdateSchemaManager:
    __slots__ = ("_client", "_tasks_depend_on_node")

    def __init__(self, client: Client):
        self._client = client
        self._tasks_depend_on_node: list[asyncio.Task] = []

    async def run_updates(self):
        """Run through schema migrations"""

        current_version = await self._client.lib_db_manager.get_bot_db_version().fetch_version()
        await run_migration_0002(self._client, current_version)
        await run_migration_0320(self._client, current_version)
        await run_migration_0330(self._client, current_version)
        await run_migration_0340(self._client, current_version)
        await run_migration_0350(self._client, current_version)
        await run_migration_0360(self._client, current_version)
        await run_migration_0760(self._client, current_version)
        await run_migration_0850(self._client, current_version)
        await run_migration_0880(self._client, current_version)
        await run_migration_0920(self._client, current_version)
        await run_migration_01050(self._client, current_version)
        await run_migration_01130(self._client, current_version)
        await run_migration_01180(self._client, current_version)
        await run_migration_010000(self._client, current_version)
        await set_current_version(self._client)
        await set_correct_ram_cap(self._client)

    async def run_deferred_tasks_which_depend_on_node(self):
        for coro in self._tasks_depend_on_node:
            try:
                await coro
            except Exception as e:
                LOGGER.error("Error running deferred task - %s", coro.get_name(), exc_info=e)
