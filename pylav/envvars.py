from __future__ import annotations

import os
import pathlib
from copy import deepcopy

import yaml
from deepdiff import DeepDiff

from pylav._logging import getLogger

LOGGER = getLogger("PyLav.Environment")

ENV_FILE = pathlib.Path.home() / "pylav.yaml"


def __get_path(path: str) -> str:
    from pylav.utils import get_true_path

    return get_true_path(path, fallback=path)


if not ENV_FILE.exists():
    LOGGER.warning(
        "%s does not exist - This is not a problem if it does then the environment variables will be read from it",
        ENV_FILE,
    )
    POSTGRES_PORT = os.getenv("PYLAV__POSTGRES_PORT", os.getenv("PGPORT"))
    POSTGRES_PASSWORD = os.getenv("PYLAV__POSTGRES_PASSWORD", os.getenv("PGPASSWORD"))
    POSTGRES_USER = os.getenv("PYLAV__POSTGRES_USER", os.getenv("PGUSER"))
    POSTGRES_DATABASE = os.getenv("PYLAV__POSTGRES_DB", os.getenv("PGDATABASE"))
    _POSTGRES_HOST = os.getenv("PYLAV__POSTGRES_HOST", os.getenv("PGHOST"))
    POSTGRES_SOCKET = os.getenv("PYLAV__POSTGRES_SOCKET")
    if POSTGRES_SOCKET is not None:
        POSTGRES_PORT = None
        POSTGRES_HOST = POSTGRES_SOCKET
    else:
        POSTGRES_HOST = _POSTGRES_HOST
    JAVA_EXECUTABLE = __get_path(os.getenv("PYLAV__JAVA_EXECUTABLE") or "java")
    LINKED_BOT_IDS = list(map(str.strip, os.getenv("PYLAV__LINKED_BOT_IDS", "").split("|")))
    USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE = bool(int(os.getenv("PYLAV__USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE", "0")))
    USE_BUNDLED_EXTERNAL_PYLAV_NODE = bool(int(os.getenv("PYLAV__USE_BUNDLED_EXTERNAL_PYLAV_NODE", "1")))

    REDIS_FULL_ADDRESS_RESPONSE_CACHE = os.getenv("PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE")

    EXTERNAL_UNMANAGED_HOST = os.getenv("PYLAV__EXTERNAL_UNMANAGED_HOST")
    EXTERNAL_UNMANAGED_PORT = int(os.getenv("PYLAV__EXTERNAL_UNMANAGED_PORT", "80"))
    EXTERNAL_UNMANAGED_PASSWORD = os.getenv("PYLAV__EXTERNAL_UNMANAGED_PASSWORD")
    EXTERNAL_UNMANAGED_SSL = bool(int(os.getenv("PYLAV__EXTERNAL_UNMANAGED_SSL", 0)))
    CACHING_ENABLED = bool(int(os.getenv("PYLAV__CACHING_ENABLED", "0")))

    TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS = max(
        int(os.getenv("PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS", "1")), 1
    )
    TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS = max(
        int(os.getenv("PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS", "7")), 7
    )
    TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS = max(
        int(os.getenv("PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS", "7")), 7
    )

    data = {
        "PYLAV__POSTGRES_PORT": POSTGRES_PORT,
        "PYLAV__POSTGRES_PASSWORD": POSTGRES_PASSWORD,
        "PYLAV__POSTGRES_USER": POSTGRES_USER,
        "PYLAV__POSTGRES_DB": POSTGRES_DATABASE,
        "PYLAV__POSTGRES_SOCKET": POSTGRES_SOCKET,
        "PYLAV__POSTGRES_HOST": _POSTGRES_HOST,
        "PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE": REDIS_FULL_ADDRESS_RESPONSE_CACHE,
        "PYLAV__JAVA_EXECUTABLE": JAVA_EXECUTABLE,
        "PYLAV__LINKED_BOT_IDS": LINKED_BOT_IDS,
        "PYLAV__USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE": USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE,
        "PYLAV__USE_BUNDLED_EXTERNAL_PYLAV_NODE": USE_BUNDLED_EXTERNAL_PYLAV_NODE,
        "PYLAV__EXTERNAL_UNMANAGED_HOST": EXTERNAL_UNMANAGED_HOST,
        "PYLAV__EXTERNAL_UNMANAGED_PORT": EXTERNAL_UNMANAGED_PORT,
        "PYLAV__EXTERNAL_UNMANAGED_PASSWORD": EXTERNAL_UNMANAGED_PASSWORD,
        "PYLAV__EXTERNAL_UNMANAGED_SSL": EXTERNAL_UNMANAGED_SSL,
        "PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS": TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS,
        "PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS": TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS,
        "PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS": TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS,
        "PYLAV__CACHING_ENABLED": CACHING_ENABLED,
    }
    with ENV_FILE.open(mode="w") as file:
        LOGGER.debug("Creating %s with the following content: %r", ENV_FILE, data)
        yaml.safe_dump(data, file, default_flow_style=False, sort_keys=False, encoding="utf-8")

else:
    LOGGER.info("%s exist - Environment variables will be read from it", ENV_FILE)
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
            POSTGRES_HOST = POSTGRES_SOCKET

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
            USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE = bool(
                int(os.getenv("PYLAV__USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE", "0"))
            )
            data_new["PYLAV__USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE"] = USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE
        if (CACHING_ENABLED := data.get("PYLAV__CACHING_ENABLED")) is None:
            CACHING_ENABLED = bool(int(os.getenv("PYLAV__CACHING_ENABLED", "0")))
            data_new["PYLAV__CACHING_ENABLED"] = CACHING_ENABLED
        if (JAVA_EXECUTABLE := data.get("PYLAV__JAVA_EXECUTABLE")) is None:
            JAVA_EXECUTABLE = __get_path(os.getenv("PYLAV__JAVA_EXECUTABLE") or "java")
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

    if DeepDiff(data, data_new, ignore_order=True, max_diffs=1):
        with ENV_FILE.open(mode="w") as file:
            LOGGER.info("Updating %s with the following content: %r", ENV_FILE, data_new)
            yaml.safe_dump(data_new, file, default_flow_style=False, sort_keys=False, encoding="utf-8")
