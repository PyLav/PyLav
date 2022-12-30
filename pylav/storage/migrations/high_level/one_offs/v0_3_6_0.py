from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import Version

from pylav.constants.versions import VERSION_0_0_0, VERSION_0_3_6_0
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def migration_v_0_3_6_0(client: Client, current_version: Version) -> None:
    if current_version >= VERSION_0_3_6_0 or current_version == VERSION_0_0_0:
        return

    LOGGER.info("Running %s migration", VERSION_0_3_6_0)
    config = client.node_db_manager.bundled_node_config()
    yaml_data = await config.fetch_yaml()
    if "path" in yaml_data["logging"]:
        del yaml_data["logging"]["path"]
    if "rollingpolicy" not in yaml_data["logging"]["logback"]:
        yaml_data["logging"]["logback"] = {
            "rollingpolicy": {
                "max-file-size": yaml_data["logging"]["file"]["max-size"],
                "max-history": yaml_data["logging"]["file"]["max-history"],
                "total-size-cap": "1GB",
            }
        }
    if "max-size" in yaml_data["logging"]["file"]:
        del yaml_data["logging"]["file"]["max-size"]
    if "max-history" in yaml_data["logging"]["file"]:
        del yaml_data["logging"]["file"]["max-history"]
    await config.update_yaml(yaml_data)
    await client.lib_db_manager.update_bot_dv_version(VERSION_0_3_6_0)
