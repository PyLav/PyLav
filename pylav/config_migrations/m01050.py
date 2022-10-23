from typing import TYPE_CHECKING

from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from pylav.client import Client


async def run_migration_01050(client: "Client", current_version: LegacyVersion | Version) -> None:
    if current_version >= parse_version("0.10.5"):
        return
    from pylav.config_migrations import LOGGER

    LOGGER.info("Running 0.10.5 migration")
    config = client.node_db_manager.bundled_node_config()
    yaml_data = await config.fetch_yaml()
    plugins = yaml_data["lavalink"]["plugins"]
    keep = [
        plugin
        for plugin in plugins
        if not plugin["dependency"].startswith("com.github.Topis-Lavalink-Plugins:Topis-Source-Managers-Plugin:")
    ]
    from pylav.utils.built_in_node import NODE_DEFAULT_SETTINGS

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
    yaml_data["plugins"]["lavasrc"]["providers"].append("dzisrc:%ISRC%")
    yaml_data["plugins"]["lavasrc"]["sources"]["deezer"] = NODE_DEFAULT_SETTINGS["plugins"]["lavasrc"]["sources"][
        "deezer"
    ]
    yaml_data["plugins"]["lavasrc"]["deezer"] = NODE_DEFAULT_SETTINGS["plugins"]["lavasrc"]["deezer"]

    await config.update_yaml(yaml_data)
    from pylav.managed_node import LAVALINK_DOWNLOAD_DIR

    folder = LAVALINK_DOWNLOAD_DIR / "plugins"
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

    await client.lib_db_manager.update_bot_dv_version("0.10.5")
