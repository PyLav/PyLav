from __future__ import annotations

from typing import TYPE_CHECKING

from pylav.constants.node import NODE_DEFAULT_SETTINGS
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def update_managed_node_settings(client: Client) -> None:
    """Update the managed node settings."""
    LOGGER.info("Running migration - Updating Managed Node Settings")
    # noinspection PyProtectedMember
    config = client._node_config_manager.bundled_node_config()
    data = await config.fetch_yaml()
    data["server"]["undertow"] = NODE_DEFAULT_SETTINGS["server"]["undertow"]
    data["server"]["compression"] = NODE_DEFAULT_SETTINGS["server"]["compression"]
    await config.update_yaml(data)
