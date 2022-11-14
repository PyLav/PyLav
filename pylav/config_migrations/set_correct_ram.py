from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pylav.envvars import JAVA_EXECUTABLE

if TYPE_CHECKING:
    from pylav.client import Client


async def set_correct_ram_cap(client: "Client") -> None:
    from pylav.config_migrations import LOGGER
    from pylav.utils import get_jar_ram_actual

    LOGGER.info("Running Managed node RAM cap limiter")
    config = client.node_db_manager.bundled_node_config()
    extras = await config.fetch_extras()
    current_max_ram = extras.get("max_ram")
    if current_max_ram is None:
        return
    min_ram, max_ram, min_ram_int, max_ram_int = get_jar_ram_actual(JAVA_EXECUTABLE)
    size_name = ("", "K", "M", "G", "T")
    match = re.match(r"(\d+)([KMGT])", current_max_ram)
    if match is None:
        return
    current_max_ram_int = int(match[1])
    current_max_ram_size = match[2]
    current_max_ram_int *= 1024 ** size_name.index(current_max_ram_size)
    if current_max_ram_int > max_ram_int:
        LOGGER.debug(f"Updating maximum RAM allocation from {current_max_ram} to {max_ram}")
        extras["max_ram"] = max_ram
        await config.update_extras(extras)
    LOGGER.debug("RAM cap limiter complete")
