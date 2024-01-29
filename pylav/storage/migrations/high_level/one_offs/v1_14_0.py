from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import Version

from pylav.constants.node import NODE_DEFAULT_SETTINGS
from pylav.constants.versions import VERSION_0_0_0, VERSION_1_14_0
from pylav.extension.bundled_node import LAVALINK_DOWNLOAD_DIR
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def migration_v_1_14_0(client: Client, current_version: Version) -> None:
    if current_version >= VERSION_1_14_0 or current_version == VERSION_0_0_0:
        return

    LOGGER.info("Running %s migration", VERSION_1_14_0)
    config = client.node_db_manager.bundled_node_config()
    yaml_data = await config.fetch_yaml()
    keep = [plugin for plugin in NODE_DEFAULT_SETTINGS["lavalink"]["plugins"]]
    yaml_data["lavalink"]["plugins"] = keep

    await config.update_yaml(yaml_data)
    await client._config.update_use_bundled_pylav_external(False)
    folder = LAVALINK_DOWNLOAD_DIR / "plugins"
    if await folder.exists():
        plugin_files = [x async for x in folder.iterdir() if x.suffix == ".jar" and x.is_file()]
        for file in plugin_files:
            try:
                await file.unlink()
            except Exception as exc:
                LOGGER.error("Failed to remove plugin: %s", file.name, exc_info=exc)

    await client.lib_db_manager.update_bot_dv_version(VERSION_1_14_0)
