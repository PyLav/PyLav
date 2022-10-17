from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from pylav.client import Client


async def run_migration_01130(client: "Client", current_version: LegacyVersion | Version) -> None:
    if current_version >= parse_version("0.11.3"):
        return
    from pylav.config_migrations import LOGGER

    LOGGER.info("Running 0.11.3 migration")
    config = client.node_db_manager.bundled_node_config()
    yaml_data = await config.fetch_yaml()
    keep = []
    _temp = set()
    for plugin in yaml_data["lavalink"]["plugins"]:
        if plugin["dependency"] not in _temp:
            keep.append(plugin)
            _temp.add(plugin["dependency"])
    yaml_data["lavalink"]["plugins"] = keep
    await config.update_yaml(yaml_data)
    await client.lib_db_manager.update_bot_dv_version("0.11.3")
