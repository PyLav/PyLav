import contextlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pylav.client import Client


async def set_current_version(client: "Client") -> None:
    from pylav import __VERSION__
    from pylav.config_migrations import LOGGER
    from pylav.exceptions import EntryNotFoundError

    LOGGER.info("Running migration cleanup")
    with contextlib.suppress(EntryNotFoundError):
        config = client.node_db_manager.bundled_node_config()
        await config.update_resume_key(f"PyLav/{client.lib_version}-{client.bot_id}")
    await client.lib_db_manager.update_bot_dv_version(__VERSION__)
