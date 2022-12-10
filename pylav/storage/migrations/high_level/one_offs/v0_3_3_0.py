from __future__ import annotations

from packaging.version import Version

from pylav.constants.versions import VERSION_0_0_0, VERSION_0_3_3_0
from pylav.storage.migrations.logging import LOGGER


async def migration_v_0_3_3_0(client: Client, current_version: Version) -> None:
    if current_version >= VERSION_0_3_3_0 or current_version == VERSION_0_0_0:
        return

    LOGGER.info("Running %s migration", VERSION_0_3_3_0)
    config = client.node_db_manager.bundled_node_config()
    yaml_data = await config.fetch_yaml()
    yaml_data["lavalink"]["server"]["youtubeConfig"] = {"email": "", "password": ""}
    await config.update_yaml(yaml_data)
    await client.lib_db_manager.update_bot_dv_version(VERSION_0_3_3_0)
