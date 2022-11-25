from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from pylav.client import Client


async def run_migration_010000(client: "Client", current_version: LegacyVersion | Version) -> None:
    if current_version >= parse_version("1.0.0"):
        return
    from pylav.config_migrations import LOGGER
    from pylav.envvars import ENV_FILE
    from pylav.utils.built_in_node import NODE_DEFAULT_SETTINGS

    LOGGER.info("Running 1.0.0 migration")
    config = client.node_db_manager.bundled_node_config()
    yaml_data = await config.fetch_yaml()
    yaml_data["lavalink"]["server"]["playerUpdateInterval"] = NODE_DEFAULT_SETTINGS["lavalink"]["server"][
        "playerUpdateInterval"
    ]
    yaml_data["lavalink"]["server"]["filters"] = NODE_DEFAULT_SETTINGS["lavalink"]["server"]["filters"]
    yaml_data["plugins"]["lavasrc"]["providers"] = list(
        dict.fromkeys(NODE_DEFAULT_SETTINGS["plugins"]["lavasrc"]["providers"])
    )
    yaml_data["plugins"]["lavasrc"]["applemusic"]["mediaAPIToken"] = NODE_DEFAULT_SETTINGS["plugins"]["lavasrc"][
        "applemusic"
    ]["mediaAPIToken"]
    yaml_data["logging"]["request"] = NODE_DEFAULT_SETTINGS["logging"]["request"]

    if yaml_data["plugins"]["lavasrc"]["spotify"]["clientId"] == "3d5cd36c73924786aa290798b2131c58":
        yaml_data["plugins"]["lavasrc"]["spotify"]["clientId"] = ""
        yaml_data["plugins"]["lavasrc"]["spotify"]["clientSecret"] = ""
        yaml_data["plugins"]["lavasrc"]["sources"]["spotify"] = False
        LOGGER.error(
            "You are using the default Spotify client ID and secret. "
            "Please register your own client ID and secret at https://developer.spotify.com/dashboard/applications "
            "and set them in your %s config file.",
            ENV_FILE,
        )

    await config.update_yaml(yaml_data)
    await client.lib_db_manager.update_bot_dv_version("1.0.0")
