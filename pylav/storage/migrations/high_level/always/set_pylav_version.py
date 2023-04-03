from __future__ import annotations

from typing import TYPE_CHECKING

from pylav import VERSION
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def set_current_version(client: Client) -> None:
    """Set the current version in the database."""
    LOGGER.info("Running migration cleanup")
    await client.lib_db_manager.update_bot_dv_version(VERSION)
