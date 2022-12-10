from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from packaging.version import Version

from pylav.constants.playlists import BUNDLED_PYLAV_PLAYLISTS_IDS
from pylav.constants.versions import VERSION_0_0_0, VERSION_0_8_5_0
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def migration_v_0_8_5_0(client: Client, current_version: Version) -> None:
    if current_version >= VERSION_0_8_5_0 or current_version == VERSION_0_0_0:
        return

    LOGGER.info("Running %s migration", VERSION_0_8_5_0)
    playlists = [
        p for p in await client.playlist_db_manager.get_bundled_playlists() if p.id in BUNDLED_PYLAV_PLAYLISTS_IDS
    ]
    for playlist in playlists:
        await playlist.delete()
    t = asyncio.create_task(client.playlist_db_manager.update_bundled_playlists(*BUNDLED_PYLAV_PLAYLISTS_IDS))
    t.set_name(f"Update bundled playlists for migration {VERSION_0_8_5_0}")
    # noinspection PyProtectedMember
    client._update_schema_manager._tasks_depend_on_node.append(t)
    await client.lib_db_manager.update_bot_dv_version(VERSION_0_8_5_0)
