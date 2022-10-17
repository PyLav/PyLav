from typing import TYPE_CHECKING

from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from pylav.client import Client


async def run_migration_0360(client: "Client", current_version: LegacyVersion | Version) -> None:
    if current_version >= parse_version("0.3.6"):
        return
    from pylav.config_migrations import LOGGER

    LOGGER.info("Running 0.3.6.0 migration")
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
    await client.lib_db_manager.update_bot_dv_version("0.3.6")
