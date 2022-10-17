from typing import TYPE_CHECKING

from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from pylav.client import Client


async def run_migration_0330(client: "Client", current_version: LegacyVersion | Version) -> None:
    if current_version >= parse_version("0.3.3"):
        return
    from pylav.config_migrations import LOGGER

    LOGGER.info("Running 0.3.3.0 migration")
    config = client.node_db_manager.bundled_node_config()
    yaml_data = await config.fetch_yaml()
    yaml_data["lavalink"]["server"]["youtubeConfig"] = {"email": "", "password": ""}
    await config.update_yaml(yaml_data)
    await client.lib_db_manager.update_bot_dv_version("0.3.3")