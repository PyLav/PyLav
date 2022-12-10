from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import Version

from pylav.constants.node import NODE_DEFAULT_SETTINGS
from pylav.constants.versions import VERSION_0_0_0, VERSION_0_10_5_0
from pylav.extension.bundled_node import LAVALINK_DOWNLOAD_DIR
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def migration_v_0_10_5_0(client: Client, current_version: Version) -> None:
    if current_version >= VERSION_0_10_5_0 or current_version == VERSION_0_0_0:
        return

    LOGGER.info("Running %s migration", VERSION_0_10_5_0)
    config = client.node_db_manager.bundled_node_config()
    yaml_data = await config.fetch_yaml()
    plugins = yaml_data["lavalink"]["plugins"]
    keep = [
        plugin
        for plugin in plugins
        if not plugin["dependency"].startswith("com.github.Topis-Lavalink-Plugins:Topis-Source-Managers-Plugin:")
    ]

    keep.extend(
        [
            plugin
            for plugin in NODE_DEFAULT_SETTINGS["lavalink"]["plugins"]
            if plugin["dependency"].startswith("com.github.TopiSenpai.LavaSrc:lavasrc-plugin")
        ]
    )
    yaml_data["lavalink"]["plugins"] = keep
    if "topissourcemanagers" in yaml_data["plugins"]:
        yaml_data["plugins"]["lavasrc"] = yaml_data["plugins"]["topissourcemanagers"]
        del yaml_data["plugins"]["topissourcemanagers"]
    if "dzisrc:%ISRC%" not in yaml_data["plugins"]["lavasrc"]["providers"]:
        yaml_data["plugins"]["lavasrc"]["providers"].append("dzisrc:%ISRC%")
    yaml_data["plugins"]["lavasrc"]["sources"]["deezer"] = NODE_DEFAULT_SETTINGS["plugins"]["lavasrc"]["sources"][
        "deezer"
    ]
    yaml_data["plugins"]["lavasrc"]["deezer"] = NODE_DEFAULT_SETTINGS["plugins"]["lavasrc"]["deezer"]

    await config.update_yaml(yaml_data)

    folder = LAVALINK_DOWNLOAD_DIR / "plugins"
    if await folder.exists():
        plugin_files = [
            x
            async for x in folder.iterdir()
            if x.name.startswith("Topis-Source-Managers-Plugin-") and x.suffix == ".jar" and x.is_file()
        ]
        for file in plugin_files:
            try:
                await file.unlink()
            except Exception as exc:
                LOGGER.error("Failed to remove plugin: %s", file.name, exc_info=exc)

    await client.lib_db_manager.update_bot_dv_version(VERSION_0_10_5_0)
