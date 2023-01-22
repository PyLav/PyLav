from __future__ import annotations

import os
import pathlib
import sys

import aiopath  # type: ignore
import platformdirs

# noinspection PyProtectedMember
from pylav._internals.pylav_yaml_builder import build_from_envvars
from pylav.logging import getLogger

LOGGER = getLogger("PyLav.Environment")

INSTANCE_NAME = None

if (data_folder := os.getenv("PYLAV__DATA_FOLDER")) is not None:
    DATA_FOLDER = pathlib.Path(data_folder)
    del data_folder
else:
    DATA_FOLDER = pathlib.Path.home()

ENV_FILE: pathlib.Path = pathlib.Path(os.getenv("PYLAV__YAML_CONFIG", DATA_FOLDER / "pylav.yaml"))


if not ENV_FILE.exists():
    LOGGER.warning(
        "%s does not exist - This is not a problem if it does then the environment variables will be read from it",
        ENV_FILE,
    )
    build_from_envvars()
    from pylav.constants.config.env_var import DATA_FOLDER as DATA_FOLDER
    from pylav.constants.config.env_var import DEFAULT_SEARCH_SOURCE as DEFAULT_SEARCH_SOURCE
    from pylav.constants.config.env_var import EXTERNAL_UNMANAGED_HOST as EXTERNAL_UNMANAGED_HOST
    from pylav.constants.config.env_var import EXTERNAL_UNMANAGED_NAME as EXTERNAL_UNMANAGED_NAME
    from pylav.constants.config.env_var import EXTERNAL_UNMANAGED_PASSWORD as EXTERNAL_UNMANAGED_PASSWORD
    from pylav.constants.config.env_var import EXTERNAL_UNMANAGED_PORT as EXTERNAL_UNMANAGED_PORT
    from pylav.constants.config.env_var import EXTERNAL_UNMANAGED_SSL as EXTERNAL_UNMANAGED_SSL
    from pylav.constants.config.env_var import FALLBACK_POSTGREST_HOST as FALLBACK_POSTGREST_HOST
    from pylav.constants.config.env_var import JAVA_EXECUTABLE as JAVA_EXECUTABLE
    from pylav.constants.config.env_var import LINKED_BOT_IDS as LINKED_BOT_IDS
    from pylav.constants.config.env_var import LOCAL_TRACKS_FOLDER as LOCAL_TRACKS_FOLDER
    from pylav.constants.config.env_var import MANAGED_NODE_APPLE_MUSIC_API_KEY as MANAGED_NODE_APPLE_MUSIC_API_KEY
    from pylav.constants.config.env_var import (
        MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE as MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE,
    )
    from pylav.constants.config.env_var import MANAGED_NODE_DEEZER_KEY as MANAGED_NODE_DEEZER_KEY
    from pylav.constants.config.env_var import MANAGED_NODE_SPOTIFY_CLIENT_ID as MANAGED_NODE_SPOTIFY_CLIENT_ID
    from pylav.constants.config.env_var import MANAGED_NODE_SPOTIFY_CLIENT_SECRET as MANAGED_NODE_SPOTIFY_CLIENT_SECRET
    from pylav.constants.config.env_var import MANAGED_NODE_SPOTIFY_COUNTRY_CODE as MANAGED_NODE_SPOTIFY_COUNTRY_CODE
    from pylav.constants.config.env_var import (
        MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN as MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN,
    )
    from pylav.constants.config.env_var import POSTGRES_DATABASE as POSTGRES_DATABASE
    from pylav.constants.config.env_var import POSTGRES_HOST as POSTGRES_HOST
    from pylav.constants.config.env_var import POSTGRES_PASSWORD as POSTGRES_PASSWORD
    from pylav.constants.config.env_var import POSTGRES_PORT as POSTGRES_PORT
    from pylav.constants.config.env_var import POSTGRES_SOCKET as POSTGRES_SOCKET
    from pylav.constants.config.env_var import POSTGRES_USER as POSTGRES_USER
    from pylav.constants.config.env_var import PREFER_PARTIAL_TRACKS as PREFER_PARTIAL_TRACKS
    from pylav.constants.config.env_var import READ_CACHING_ENABLED as READ_CACHING_ENABLED
    from pylav.constants.config.env_var import REDIS_FULL_ADDRESS_RESPONSE_CACHE as REDIS_FULL_ADDRESS_RESPONSE_CACHE
    from pylav.constants.config.env_var import (
        TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS as TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS,
    )
    from pylav.constants.config.env_var import (
        TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS as TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS,
    )
    from pylav.constants.config.env_var import (
        TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS as TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS,
    )
    from pylav.constants.config.env_var import USE_BUNDLED_EXTERNAL_PYLAV_NODE as USE_BUNDLED_EXTERNAL_PYLAV_NODE
else:
    LOGGER.info("%s exist - Environment variables will be read from it", ENV_FILE)
    # Apply environment variables overrides if they exist
    from pylav.constants.config import overrides
    from pylav.constants.config.file import DATA_FOLDER as DATA_FOLDER
    from pylav.constants.config.file import DEFAULT_SEARCH_SOURCE as DEFAULT_SEARCH_SOURCE
    from pylav.constants.config.file import EXTERNAL_UNMANAGED_HOST as EXTERNAL_UNMANAGED_HOST
    from pylav.constants.config.file import EXTERNAL_UNMANAGED_NAME as EXTERNAL_UNMANAGED_NAME
    from pylav.constants.config.file import EXTERNAL_UNMANAGED_PASSWORD as EXTERNAL_UNMANAGED_PASSWORD
    from pylav.constants.config.file import EXTERNAL_UNMANAGED_PORT as EXTERNAL_UNMANAGED_PORT
    from pylav.constants.config.file import EXTERNAL_UNMANAGED_SSL as EXTERNAL_UNMANAGED_SSL
    from pylav.constants.config.file import FALLBACK_POSTGREST_HOST as FALLBACK_POSTGREST_HOST
    from pylav.constants.config.file import JAVA_EXECUTABLE as JAVA_EXECUTABLE
    from pylav.constants.config.file import LINKED_BOT_IDS as LINKED_BOT_IDS
    from pylav.constants.config.file import LOCAL_TRACKS_FOLDER as LOCAL_TRACKS_FOLDER
    from pylav.constants.config.file import MANAGED_NODE_APPLE_MUSIC_API_KEY as MANAGED_NODE_APPLE_MUSIC_API_KEY
    from pylav.constants.config.file import (
        MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE as MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE,
    )
    from pylav.constants.config.file import MANAGED_NODE_DEEZER_KEY as MANAGED_NODE_DEEZER_KEY
    from pylav.constants.config.file import MANAGED_NODE_SPOTIFY_CLIENT_ID as MANAGED_NODE_SPOTIFY_CLIENT_ID
    from pylav.constants.config.file import MANAGED_NODE_SPOTIFY_CLIENT_SECRET as MANAGED_NODE_SPOTIFY_CLIENT_SECRET
    from pylav.constants.config.file import MANAGED_NODE_SPOTIFY_COUNTRY_CODE as MANAGED_NODE_SPOTIFY_COUNTRY_CODE
    from pylav.constants.config.file import (
        MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN as MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN,
    )
    from pylav.constants.config.file import POSTGRES_DATABASE as POSTGRES_DATABASE
    from pylav.constants.config.file import POSTGRES_HOST as POSTGRES_HOST
    from pylav.constants.config.file import POSTGRES_PASSWORD as POSTGRES_PASSWORD
    from pylav.constants.config.file import POSTGRES_PORT as POSTGRES_PORT
    from pylav.constants.config.file import POSTGRES_SOCKET as POSTGRES_SOCKET
    from pylav.constants.config.file import POSTGRES_USER as POSTGRES_USER
    from pylav.constants.config.file import PREFER_PARTIAL_TRACKS as PREFER_PARTIAL_TRACKS
    from pylav.constants.config.file import READ_CACHING_ENABLED as READ_CACHING_ENABLED
    from pylav.constants.config.file import REDIS_FULL_ADDRESS_RESPONSE_CACHE as REDIS_FULL_ADDRESS_RESPONSE_CACHE
    from pylav.constants.config.file import (
        TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS as TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS,
    )
    from pylav.constants.config.file import (
        TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS as TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS,
    )
    from pylav.constants.config.file import (
        TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS as TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS,
    )
    from pylav.constants.config.file import USE_BUNDLED_EXTERNAL_PYLAV_NODE as USE_BUNDLED_EXTERNAL_PYLAV_NODE

    for item in dir(overrides):
        if item.startswith("__") or not item.isupper():
            continue
        if (val := getattr(overrides, item, None)) is None:
            continue
        LOGGER.warning("Environment Variable found: Overriding PYLAV__%s with %s", item, val)
        setattr(sys.modules[__name__], item, val)


BROTLI_ENABLED = False

if DATA_FOLDER is None:
    LIB_DIR = platformdirs.PlatformDirs("PyLav")
    __CONFIG_DIR = pathlib.Path(LIB_DIR.user_config_path)
    if sys.platform == "linux" and 0 < os.getuid() < 1000 and not pathlib.Path.home().exists():
        __CONFIG_DIR = pathlib.Path(LIB_DIR.site_data_path)
else:
    __CONFIG_DIR = pathlib.Path(DATA_FOLDER)

__CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR = aiopath.AsyncPath(__CONFIG_DIR)
