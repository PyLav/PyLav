from __future__ import annotations

import base64
import os

# noinspection PyProtectedMember
from pylav._internals.functions import _get_path as __get_path
from pylav._internals.functions import fix
from pylav.constants.node_features import SUPPORTED_SEARCHES as __SUPPORTED_SEARCHES
from pylav.constants.specials import _MAPPING, ANIME
from pylav.logging import getLogger as __getLogger

__LOGGER = __getLogger("PyLav.Environment")

LOCAL_DEBUGGING = os.getenv("PYLAV__DEBUGGING")

POSTGRES_HOST = os.getenv("PYLAV__POSTGRES_HOST")
# noinspection SpellCheckingInspection
POSTGRES_PORT = os.getenv("PYLAV__POSTGRES_PORT")
# noinspection SpellCheckingInspection
POSTGRES_PASSWORD = os.getenv("PYLAV__POSTGRES_PASSWORD")
# noinspection SpellCheckingInspection
POSTGRES_USER = os.getenv("PYLAV__POSTGRES_USER")
# noinspection SpellCheckingInspection
POSTGRES_DATABASE = os.getenv("PYLAV__POSTGRES_DB")
POSTGRES_SOCKET = os.getenv("PYLAV__POSTGRES_SOCKET")
POSTGRES_CONNECTIONS = (
    max(int(envar_value), 4) if (envar_value := os.getenv("PYLAV__POSTGRES_CONNECTIONS")) is not None else None
)

FALLBACK_POSTGREST_HOST = POSTGRES_HOST
if POSTGRES_SOCKET is not None:
    POSTGRES_PORT = None
    POSTGRES_HOST = POSTGRES_SOCKET
JAVA_EXECUTABLE = __get_path(envar_value) if (envar_value := os.getenv("PYLAV__JAVA_EXECUTABLE")) is not None else None

REDIS_FULL_ADDRESS_RESPONSE_CACHE = os.getenv("PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE")

EXTERNAL_UNMANAGED_HOST = os.getenv("PYLAV__EXTERNAL_UNMANAGED_HOST")
EXTERNAL_UNMANAGED_PORT = (
    int(envar_value) if (envar_value := os.getenv("PYLAV__EXTERNAL_UNMANAGED_PORT")) is not None else None
)
EXTERNAL_UNMANAGED_PASSWORD = os.getenv("PYLAV__EXTERNAL_UNMANAGED_PASSWORD")
EXTERNAL_UNMANAGED_SSL = (
    bool(int(envar_value)) if (envar_value := os.getenv("PYLAV__EXTERNAL_UNMANAGED_SSL")) is not None else None
)
EXTERNAL_UNMANAGED_NAME = os.getenv("PYLAV__EXTERNAL_UNMANAGED_NAME")

READ_CACHING_ENABLED = (
    bool(int(envar_value)) if (envar_value := os.getenv("PYLAV__READ_CACHING_ENABLED")) is not None else None
)

TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS = (
    max(int(envar_value), 1)
    if (envar_value := os.getenv("PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS")) is not None
    else None
)

TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS = (
    max(int(envar_value), 7)
    if (envar_value := os.getenv("PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS")) is not None
    else None
)


TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS = (
    max(int(envar_value), 7)
    if (envar_value := os.getenv("PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS")) is not None
    else None
)


# noinspection SpellCheckingInspection
DEFAULT_SEARCH_SOURCE = os.getenv("PYLAV__DEFAULT_SEARCH_SOURCE")
if DEFAULT_SEARCH_SOURCE is not None and DEFAULT_SEARCH_SOURCE not in __SUPPORTED_SEARCHES:
    DEFAULT_SEARCH_SOURCE = None

MANAGED_NODE_SPOTIFY_CLIENT_ID = os.getenv("PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_ID")
MANAGED_NODE_SPOTIFY_CLIENT_SECRET = os.getenv("PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_SECRET")
MANAGED_NODE_SPOTIFY_COUNTRY_CODE = os.getenv("PYLAV__MANAGED_NODE_SPOTIFY_COUNTRY_CODE")
MANAGED_NODE_APPLE_MUSIC_API_KEY = os.getenv("PYLAV__MANAGED_NODE_APPLE_MUSIC_API_KEY")
MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE = os.getenv("PYLAV__MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE")
MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN = os.getenv("PYLAV__MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN")
MANAGED_NODE_DEEZER_KEY = os.getenv("PYLAV__MANAGED_NODE_DEEZER_KEY") or ANIME
if MANAGED_NODE_DEEZER_KEY and MANAGED_NODE_DEEZER_KEY.startswith("id"):
    _temp = [MANAGED_NODE_DEEZER_KEY[i : i + 16] for i in range(0, len(MANAGED_NODE_DEEZER_KEY), 16)]
    MANAGED_NODE_DEEZER_KEY = "".join(
        [
            base64.b64decode(r).decode()
            for r in [
                fix(_temp[2], _MAPPING[2]),
                fix(_temp[1], _MAPPING[1]),
                fix(_temp[3], _MAPPING[3]),
                fix(_temp[0], _MAPPING[0]),
            ]
        ]
    )
LOCAL_TRACKS_FOLDER = os.getenv("PYLAV__LOCAL_TRACKS_FOLDER")
DATA_FOLDER = os.getenv("PYLAV__DATA_FOLDER")
ENABLE_NODE_RESUMING = (
    bool(int(envar_value)) if (envar_value := os.getenv("PYLAV__ENABLE_NODE_RESUMING")) is not None else None
)
ENABLE_NODE_RESUMING = False
# TODO:
#  - Add support for resuming nodes

DEFAULT_PLAYER_VOLUME = (
    max(int(envar_value), 1) if (envar_value := os.getenv("PYLAV__DEFAULT_PLAYER_VOLUME")) is not None else None
)
