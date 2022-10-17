from typing import TYPE_CHECKING

from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from pylav.client import Client


async def run_migration_0850(client: "Client", current_version: LegacyVersion | Version) -> None:
    if current_version >= parse_version("0.8.5"):
        return

    from pylav.config_migrations import LOGGER

    LOGGER.info("Running 0.8.5.0 migration")
    playlists = [p for p in await client.playlist_db_manager.get_bundled_playlists() if p.id in {1, 2}]
    for playlist in playlists:
        await playlist.delete()
    await client.playlist_db_manager.update_bundled_playlists(1, 2)
    await client.lib_db_manager.update_bot_dv_version("0.8.5")
