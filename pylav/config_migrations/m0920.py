from typing import TYPE_CHECKING

from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from pylav.client import Client


async def run_migration_0920(client: "Client", current_version: LegacyVersion | Version) -> None:
    if current_version >= parse_version("0.9.2"):
        return
    from pylav.config_migrations import LOGGER

    LOGGER.info("Running 0.9.2 migration")
    await client.player_state_db_manager.delete_all_players()
    await client.lib_db_manager.update_bot_dv_version("0.9.2")
