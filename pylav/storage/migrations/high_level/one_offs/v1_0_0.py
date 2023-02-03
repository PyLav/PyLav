from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import Version

# noinspection PyProtectedMember
from pylav._internals.pylav_yaml_builder import ENV_FILE
from pylav.constants.node import NODE_DEFAULT_SETTINGS
from pylav.constants.versions import VERSION_0_0_0, VERSION_1_0_0
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def migration_v_1_0_0(client: Client, current_version: Version) -> None:
    if current_version >= VERSION_1_0_0 or current_version == VERSION_0_0_0:
        return

    LOGGER.info("Running %s migration", VERSION_1_0_0)
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
            "Please register your own client ID and secret at "
            "https://developer.spotify.com/dashboard/applications "
            "and set them in your %s settings file.",
            ENV_FILE,
        )
    yaml_data["lavalink"]["server"]["resamplingQuality"] = NODE_DEFAULT_SETTINGS["lavalink"]["server"][
        "resamplingQuality"
    ]
    await config.update_yaml(yaml_data)
    await client.lib_db_manager.update_bot_dv_version(VERSION_1_0_0)
