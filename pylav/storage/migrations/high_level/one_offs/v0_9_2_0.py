from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import Version

from pylav.constants.versions import VERSION_0_0_0, VERSION_0_9_2_0
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def migration_v_0_9_2_0(client: Client, current_version: Version) -> None:
    if current_version >= VERSION_0_9_2_0 or current_version == VERSION_0_0_0:
        return

    LOGGER.info("Running %s migration", VERSION_0_9_2_0)
    await client.player_state_db_manager.delete_all_players()
    await client.lib_db_manager.update_bot_dv_version(VERSION_0_9_2_0)
