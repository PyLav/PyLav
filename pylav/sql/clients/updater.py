from __future__ import annotations

from typing import TYPE_CHECKING

from pylav.config_migrations.m0002 import run_0002_migration
from pylav.config_migrations.m0320 import run_0320_migration
from pylav.config_migrations.m0330 import run_0330_migration
from pylav.config_migrations.m0340 import run_0340_migration
from pylav.config_migrations.m0350 import run_0350_migration
from pylav.config_migrations.m0360 import run_0360_migration
from pylav.config_migrations.m0760 import run_0760_migration
from pylav.config_migrations.m0850 import run_0850_migration
from pylav.config_migrations.m0880 import run_0880_migration
from pylav.config_migrations.m0920 import run_0920_migration
from pylav.config_migrations.m01050 import run_01050_migration
from pylav.config_migrations.m01130 import run_01130_migration
from pylav.config_migrations.set_current_version import set_current_version
from pylav.config_migrations.update_plugins import update_plugins

if TYPE_CHECKING:
    from pylav.client import Client


class UpdateSchemaManager:
    __slots__ = ("_client",)

    def __init__(self, client: Client):
        self._client = client

    async def run_updates(self):
        """Run through schema migrations"""

        current_version = await self._client.lib_db_manager.get_bot_db_version().fetch_version()

        await run_0002_migration(self._client, current_version)
        await run_0320_migration(self._client, current_version)
        await run_0330_migration(self._client, current_version)
        await run_0340_migration(self._client, current_version)
        await run_0350_migration(self._client, current_version)
        await run_0360_migration(self._client, current_version)
        await run_0760_migration(self._client, current_version)
        await run_0850_migration(self._client, current_version)
        await run_0880_migration(self._client, current_version)
        await run_0920_migration(self._client, current_version)
        await run_01050_migration(self._client, current_version)
        await run_01130_migration(self._client, current_version)
        await set_current_version(self._client)
        await update_plugins(self._client)
