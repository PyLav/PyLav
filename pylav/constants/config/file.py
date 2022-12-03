import base64
import os
from copy import deepcopy

import yaml
from deepdiff import DeepDiff  # type: ignore

from pylav._internals.functions import _get_path
from pylav.constants.config import ENV_FILE
from pylav.constants.node_features import SUPPORTED_SEARCHES
from pylav.constants.specials import ANIME
from pylav.logging import getLogger

LOGGER = getLogger("PyLav.Environment")

with ENV_FILE.open(mode="r") as file:
    data = yaml.safe_load(file.read())
    data_new = deepcopy(data)
    if (POSTGRES_PORT := data.get("PYLAV__POSTGRES_PORT")) is None:
        POSTGRES_PORT = os.getenv("PYLAV__POSTGRES_PORT", os.getenv("PGPORT"))
        data_new["PYLAV__POSTGRES_PORT"] = POSTGRES_PORT

    if (POSTGRES_PASSWORD := data.get("PYLAV__POSTGRES_PASSWORD")) is None:
        POSTGRES_PASSWORD = os.getenv("PYLAV__POSTGRES_PASSWORD", os.getenv("PGPASSWORD"))
        data_new["PYLAV__POSTGRES_PASSWORD"] = POSTGRES_PASSWORD

    if (POSTGRES_USER := data.get("PYLAV__POSTGRES_USER")) is None:
        POSTGRES_USER = os.getenv("PYLAV__POSTGRES_USER", os.getenv("PGUSER"))
        data_new["PYLAV__POSTGRES_USER"] = POSTGRES_USER

    if (POSTGRES_DATABASE := data.get("PYLAV__POSTGRES_DB")) is None:
        POSTGRES_DATABASE = os.getenv("PYLAV__POSTGRES_DB", os.getenv("PGDATABASE"))
        data_new["PYLAV__POSTGRES_DB"] = POSTGRES_DATABASE

    if (POSTGRES_HOST := data.get("PYLAV__POSTGRES_HOST")) is None:
        POSTGRES_HOST = os.getenv("PYLAV__POSTGRES_HOST", os.getenv("PGHOST"))
        data_new["PYLAV__POSTGRES_HOST"] = POSTGRES_HOST

    if (POSTGRES_SOCKET := data.get("PYLAV__POSTGRES_SOCKET")) is None:
        POSTGRES_SOCKET = os.getenv("PYLAV__POSTGRES_SOCKET")
        data_new["PYLAV__POSTGRES_SOCKET"] = POSTGRES_SOCKET

    if POSTGRES_SOCKET is not None:
        POSTGRES_PORT = None
        FALLBACK_POSTGREST_HOST = POSTGRES_HOST
        POSTGRES_HOST = POSTGRES_SOCKET
    else:
        FALLBACK_POSTGREST_HOST = POSTGRES_HOST

    if (REDIS_FULL_ADDRESS_RESPONSE_CACHE := data.get("PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE")) is None:
        REDIS_FULL_ADDRESS_RESPONSE_CACHE = os.getenv("PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE")
        data_new["PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE"] = REDIS_FULL_ADDRESS_RESPONSE_CACHE

    if (LINKED_BOT_IDS := data.get("PYLAV__LINKED_BOT_IDS")) is None:
        LINKED_BOT_IDS = list(map(str.strip, os.getenv("PYLAV__LINKED_BOT_IDS", "").split("|")))
        data_new["PYLAV__LINKED_BOT_IDS"] = LINKED_BOT_IDS

    if (USE_BUNDLED_EXTERNAL_PYLAV_NODE := data.get("PYLAV__USE_BUNDLED_EXTERNAL_PYLAV_NODE")) is None:
        USE_BUNDLED_EXTERNAL_PYLAV_NODE = bool(int(os.getenv("PYLAV__USE_BUNDLED_EXTERNAL_PYLAV_NODE", "1")))
        data_new["PYLAV__USE_BUNDLED_EXTERNAL_PYLAV_NODE"] = USE_BUNDLED_EXTERNAL_PYLAV_NODE

    if (USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE := data.get("PYLAV__USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE")) is None:
        USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE = bool(int(os.getenv("PYLAV__USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE", "0")))
        data_new["PYLAV__USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE"] = USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE
    if (READ_CACHING_ENABLED := data.get("PYLAV__READ_CACHING_ENABLED")) is None:
        READ_CACHING_ENABLED = bool(int(os.getenv("PYLAV__READ_CACHING_ENABLED", "0")))
        data_new["PYLAV__READ_CACHING_ENABLED"] = READ_CACHING_ENABLED
    if (JAVA_EXECUTABLE := data.get("PYLAV__JAVA_EXECUTABLE")) is None:
        JAVA_EXECUTABLE = _get_path(os.getenv("PYLAV__JAVA_EXECUTABLE") or "java")
        data_new["PYLAV__JAVA_EXECUTABLE"] = JAVA_EXECUTABLE

    if (EXTERNAL_UNMANAGED_HOST := data.get("PYLAV__EXTERNAL_UNMANAGED_HOST")) is None:
        EXTERNAL_UNMANAGED_HOST = os.getenv("PYLAV__EXTERNAL_UNMANAGED_HOST")
        data_new["PYLAV__EXTERNAL_UNMANAGED_HOST"] = EXTERNAL_UNMANAGED_HOST

    if (EXTERNAL_UNMANAGED_PORT := data.get("PYLAV__EXTERNAL_UNMANAGED_PORT")) is None:
        EXTERNAL_UNMANAGED_PORT = int(os.getenv("PYLAV__EXTERNAL_UNMANAGED_PORT", "80"))
        data_new["PYLAV__EXTERNAL_UNMANAGED_PORT"] = EXTERNAL_UNMANAGED_PORT

    if (EXTERNAL_UNMANAGED_PASSWORD := data.get("PYLAV__EXTERNAL_UNMANAGED_PASSWORD")) is None:
        EXTERNAL_UNMANAGED_PASSWORD = os.getenv("PYLAV__EXTERNAL_UNMANAGED_PASSWORD")
        data_new["PYLAV__EXTERNAL_UNMANAGED_PASSWORD"] = EXTERNAL_UNMANAGED_PASSWORD

    if (EXTERNAL_UNMANAGED_SSL := data.get("PYLAV__EXTERNAL_UNMANAGED_SSL")) is None:
        EXTERNAL_UNMANAGED_SSL = bool(int(os.getenv("PYLAV__EXTERNAL_UNMANAGED_SSL", "0")))
        data_new["PYLAV__EXTERNAL_UNMANAGED_SSL"] = EXTERNAL_UNMANAGED_SSL

    if (
        TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS := data.get("PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS")
    ) is None:
        TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS = max(
            int(os.getenv("PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS", "1")), 1
        )
        data_new["PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS"] = TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS

    if (
        TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS := data.get(
            "PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS"
        )
    ) is None:
        TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS = max(
            int(os.getenv("PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS", "7")), 7
        )
        data_new[
            "PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS"
        ] = TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS

    if (
        TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS := data.get("PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS")
    ) is None:
        TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS = max(
            int(os.getenv("PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS", "7")), 7
        )
        data_new["PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS"] = TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS

    if (DEFAULT_SEARCH_SOURCE := data.get("PYLAV__DEFAULT_SEARCH_SOURCE")) is None:
        DEFAULT_SEARCH_SOURCE = os.getenv("PYLAV__DEFAULT_SEARCH_SOURCE")

    if DEFAULT_SEARCH_SOURCE not in SUPPORTED_SEARCHES:
        LOGGER.warning("Invalid search source %s, defaulting to dzsearch", DEFAULT_SEARCH_SOURCE)
        LOGGER.info("Valid search sources are %s", ", ".join(DEFAULT_SEARCH_SOURCE.keys()))
        DEFAULT_SEARCH_SOURCE = "dzsearch"
    data_new["PYLAV__DEFAULT_SEARCH_SOURCE"] = DEFAULT_SEARCH_SOURCE

    if (MANAGED_NODE_SPOTIFY_CLIENT_ID := data.get("PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_ID")) is None:
        MANAGED_NODE_SPOTIFY_CLIENT_ID = os.getenv("PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_ID", "")
        data_new["PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_ID"] = MANAGED_NODE_SPOTIFY_CLIENT_ID

    if (MANAGED_NODE_SPOTIFY_CLIENT_SECRET := data.get("PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_SECRET")) is None:
        MANAGED_NODE_SPOTIFY_CLIENT_SECRET = os.getenv("PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_SECRET") or ""
        data_new["PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_SECRET"] = MANAGED_NODE_SPOTIFY_CLIENT_SECRET

    if (MANAGED_NODE_SPOTIFY_COUNTRY_CODE := data.get("PYLAV__MANAGED_NODE_SPOTIFY_COUNTRY_CODE")) is None:
        MANAGED_NODE_SPOTIFY_COUNTRY_CODE = os.getenv("PYLAV__MANAGED_NODE_SPOTIFY_COUNTRY_CODE") or "US"
        data_new["PYLAV__MANAGED_NODE_SPOTIFY_COUNTRY_CODE"] = MANAGED_NODE_SPOTIFY_COUNTRY_CODE

    if (MANAGED_NODE_APPLE_MUSIC_API_KEY := data.get("PYLAV__MANAGED_NODE_APPLE_MUSIC_API_KEY")) is None:
        MANAGED_NODE_APPLE_MUSIC_API_KEY = os.getenv("PYLAV__MANAGED_NODE_APPLE_MUSIC_API_KEY") or ""
        data_new["PYLAV__MANAGED_NODE_APPLE_MUSIC_API_KEY"] = MANAGED_NODE_APPLE_MUSIC_API_KEY

    if (MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE := data.get("PYLAV__MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE")) is None:
        MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE = os.getenv("PYLAV__MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE") or "US"
        data_new["PYLAV__MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE"] = MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE

    if (MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN := data.get("PYLAV__MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN")) is None:
        MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN = os.getenv("PYLAV__MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN") or ""
        data_new["PYLAV__MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN"] = MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN

    if (MANAGED_NODE_DEEZER_KEY := data.get("PYLAV__MANAGED_NODE_DEEZER_KEY")) is None:
        MANAGED_NODE_DEEZER_KEY = os.getenv("PYLAV__MANAGED_NODE_DEEZER_KEY") or "".join(
            [base64.b64decode(r).decode() for r in ANIME.split(b"|")]
        )
        data_new["PYLAV__MANAGED_NODE_DEEZER_KEY"] = MANAGED_NODE_DEEZER_KEY

if DeepDiff(data, data_new, ignore_order=True, max_passes=2, cache_size=1000):
    with ENV_FILE.open(mode="w") as file:
        LOGGER.info("Updating %s with the following content: %r", ENV_FILE, data_new)
        yaml.safe_dump(data_new, file, default_flow_style=False, sort_keys=False, encoding="utf-8")
