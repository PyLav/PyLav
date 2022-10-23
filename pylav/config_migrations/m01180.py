from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from pylav.client import Client


async def run_migration_01180(client: "Client", current_version: LegacyVersion | Version) -> None:
    if current_version >= parse_version("0.11.8"):
        return
    from pylav.config_migrations import LOGGER
    from pylav.utils.built_in_node import NODE_DEFAULT_SETTINGS

    LOGGER.info("Running 0.11.8 migration")
    config = client.node_db_manager.bundled_node_config()
    yaml_data = await config.fetch_yaml()
    yaml_data["plugins"]["lavasrc"]["sources"]["yandexmusic"] = False
    yaml_data["plugins"]["lavasrc"]["yandexmusic"] = NODE_DEFAULT_SETTINGS["plugins"]["lavasrc"]["yandexmusic"]
    await config.update_yaml(yaml_data)
    await client.lib_db_manager.update_bot_dv_version("0.11.8")
