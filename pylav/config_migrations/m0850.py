import asyncio
from typing import TYPE_CHECKING

from packaging.version import Version
from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from pylav.client import Client


async def run_migration_0850(client: "Client", current_version: Version) -> None:
    if current_version >= parse_version("0.8.5"):
        return

    from pylav.config_migrations import LOGGER

    LOGGER.info("Running 0.8.5.0 migration")
    playlists = [p for p in await client.playlist_db_manager.get_bundled_playlists() if p.id in {1, 2}]
    for playlist in playlists:
        await playlist.delete()
    t = asyncio.create_task(client.playlist_db_manager.update_bundled_playlists(*BUNDLED_PYLAV_PLAYLISTS_IDS))
    t.set_name("Update bundled playlists for migration 0.8.5")
    client._update_schema_manager._tasks_depend_on_node.append(t)
