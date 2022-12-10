from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from pylav import VERSION
from pylav.exceptions.database import EntryNotFoundException
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def set_current_version(client: Client) -> None:

    LOGGER.info("Running migration cleanup")
    with contextlib.suppress(EntryNotFoundException):
        config = client.node_db_manager.bundled_node_config()
        await config.update_resume_key(f"PyLav/{VERSION}-{client.bot_id}")
    await client.lib_db_manager.update_bot_dv_version(VERSION)
