from __future__ import annotations

import asyncio

from pylav.logging import getLogger

LOGGER = getLogger("PyLav.Database.Controller.Migration")


class MigrationController:
    __slots__ = ("_client", "_tasks_depend_on_node")

    def __init__(self, client: Client):
        self._client = client
        self._tasks_depend_on_node: list[asyncio.Task] = []

    async def run_updates(self) -> None:
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

    async def run_deferred_tasks_which_depend_on_node(self) -> None:
        for coro in self._tasks_depend_on_node:
            try:
                await coro
            except Exception as e:
                LOGGER.error("Error running deferred task - %s", coro.get_name(), exc_info=e)
