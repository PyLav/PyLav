from __future__ import annotations

from typing import TYPE_CHECKING

from deepdiff import DeepDiff

from pylav.constants.node import NODE_DEFAULT_SETTINGS
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def fix_managed_node_settings(client: Client) -> None:
    """Fix the managed node settings."""
    LOGGER.info("Running migration - Fixing Managed Node Settings")
    # noinspection PyProtectedMember
    config = client._node_config_manager.bundled_node_config()
    data = await config.fetch_yaml()
    if (ddiff := DeepDiff(data, NODE_DEFAULT_SETTINGS, ignore_order=True, max_passes=3, cache_size=10000)) and (
        ddiff.get("dictionary_item_added") or ddiff.get("dictionary_item_removed")
    ):
        LOGGER.warning("Managed node settings are not IN the expected format - Force resetting it")
        await config.update_yaml(NODE_DEFAULT_SETTINGS)
