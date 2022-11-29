from typing import TYPE_CHECKING

from packaging.version import Version
from packaging.version import parse as parse_version

from pylav.constants import VERSION_ZERO

if TYPE_CHECKING:
    from pylav.client import Client


async def run_migration_0880(client: "Client", current_version: Version) -> None:
    if current_version >= parse_version("0.8.8") or current_version == VERSION_ZERO:
        return
    from pylav.config_migrations import LOGGER

    LOGGER.info("Running 0.8.8.0 migration")
    from pylav.constants import BUNDLED_NODES_IDS_HOST_MAPPING

    for node_id in BUNDLED_NODES_IDS_HOST_MAPPING:
        await client.node_db_manager.delete(node_id)
    await client.lib_db_manager.update_bot_dv_version("0.8.8")
