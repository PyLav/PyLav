from __future__ import annotations

from typing import TYPE_CHECKING

from pylav.constants.config.overrides import (
    LOCAL_TRACKS_FOLDER,
    MANAGED_NODE_APPLE_MUSIC_API_KEY,
    MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE,
    MANAGED_NODE_DEEZER_KEY,
    MANAGED_NODE_SPOTIFY_CLIENT_ID,
    MANAGED_NODE_SPOTIFY_CLIENT_SECRET,
    MANAGED_NODE_SPOTIFY_COUNTRY_CODE,
    MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN,
)
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def process_envvar_variables(client: Client) -> None:
    """Process envvar variables."""
    LOGGER.info("Running migration - Envvar variables")

    config = client.node_db_manager.bundled_node_config()
    yaml_data = await config.fetch_yaml()
    updated = False
    if MANAGED_NODE_SPOTIFY_CLIENT_ID is not None:
        yaml_data["plugins"]["lavasrc"]["spotify"]["clientId"] = MANAGED_NODE_SPOTIFY_CLIENT_ID
        updated = True
    if MANAGED_NODE_SPOTIFY_CLIENT_SECRET is not None:
        yaml_data["plugins"]["lavasrc"]["spotify"]["clientSecret"] = MANAGED_NODE_SPOTIFY_CLIENT_SECRET
        updated = True
    if MANAGED_NODE_SPOTIFY_COUNTRY_CODE is not None:
        yaml_data["plugins"]["lavasrc"]["spotify"]["countryCode"] = MANAGED_NODE_SPOTIFY_COUNTRY_CODE
        updated = True
    if MANAGED_NODE_APPLE_MUSIC_API_KEY is not None:
        yaml_data["plugins"]["lavasrc"]["applemusic"]["mediaAPIToken"] = MANAGED_NODE_APPLE_MUSIC_API_KEY
        updated = True
    if MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE is not None:
        yaml_data["plugins"]["lavasrc"]["applemusic"]["countryCode"] = MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE
        updated = True
    if MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN is not None:
        yaml_data["plugins"]["lavasrc"]["yandexmusic"]["accessToken"] = MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN
        updated = True
    if MANAGED_NODE_DEEZER_KEY is not None:
        yaml_data["plugins"]["lavasrc"]["deezer"]["masterDecryptionKey"] = MANAGED_NODE_DEEZER_KEY
        updated = True
    if updated:
        await config.update_yaml(yaml_data)

    if LOCAL_TRACKS_FOLDER is not None:
        await client.lib_db_manager.get_config().update_localtrack_folder(LOCAL_TRACKS_FOLDER)
