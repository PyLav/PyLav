from __future__ import annotations

import os
import pathlib
from copy import deepcopy

import yaml
from deepdiff import DeepDiff

from pylav._logging import getLogger

LOGGER = getLogger("PyLav.Environment")

ENV_FILE = pathlib.Path.home() / "pylav.yaml"

if not ENV_FILE.exists():
    LOGGER.warning(
        "%s does not exist - This is not a problem if it does then the environment variables will be read from it.",
        ENV_FILE,
    )
    POSTGRES_PORT = os.getenv("PYLAV__POSTGRES_PORT", os.getenv("PGPORT"))
    POSTGRES_PASSWORD = os.getenv("PYLAV__POSTGRES_PASSWORD", os.getenv("PGPASSWORD"))
    POSTGRES_USER = os.getenv("PYLAV__POSTGRES_USER", os.getenv("PGUSER"))
    POSTGRES_DATABASE = os.getenv("PYLAV__POSTGRES_DB", os.getenv("PGDATABASE"))
    POSTGRES_HOST = os.getenv("PYLAV__POSTGRES_HOST", os.getenv("PGHOST"))

    JAVA_EXECUTABLE = os.getenv("PYLAV__JAVA_EXECUTABLE", "java")
    LINKED_BOT_IDS = list(map(str.strip, os.getenv("PYLAV__LINKED_BOT_IDS", "").split("|")))
    USE_BUNDLED_EXTERNAL_NODES = bool(int(os.getenv("PYLAV__USE_BUNDLED_EXTERNAL_NODES", "1")))

    REDIS_FULL_ADDRESS_RESPONSE_CACHE = os.getenv("PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE")

    EXTERNAL_UNMANAGED_HOST = os.getenv("PYLAV__EXTERNAL_UNMANAGED_HOST")
    EXTERNAL_UNMANAGED_PORT = int(os.getenv("PYLAV__EXTERNAL_UNMANAGED_PORT", "80"))
    EXTERNAL_UNMANAGED_PASSWORD = os.getenv("PYLAV__EXTERNAL_UNMANAGED_PASSWORD")
    EXTERNAL_UNMANAGED_SSL = bool(int(os.getenv("PYLAV__EXTERNAL_UNMANAGED_SSL", 0)))

    TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS = max(int(os.getenv("PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS", "1")), 1)
    TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS = max(
        int(os.getenv("PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS", "7")), 7
    )
    TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS = max(int(os.getenv("PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS", "7")), 7)

    data = {
        "PYLAV__POSTGRES_PORT": POSTGRES_PORT,
        "PYLAV__POSTGRES_PASSWORD": POSTGRES_PASSWORD,
        "PYLAV__POSTGRES_USER": POSTGRES_USER,
        "PYLAV__POSTGRES_DB": POSTGRES_DATABASE,
        "PYLAV__POSTGRES_HOST": POSTGRES_HOST,
        "PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE": REDIS_FULL_ADDRESS_RESPONSE_CACHE,
        "PYLAV__JAVA_EXECUTABLE": JAVA_EXECUTABLE,
        "PYLAV__LINKED_BOT_IDS": LINKED_BOT_IDS,
        "PYLAV__USE_BUNDLED_EXTERNAL_NODES": USE_BUNDLED_EXTERNAL_NODES,
        "PYLAV__EXTERNAL_UNMANAGED_HOST": EXTERNAL_UNMANAGED_HOST,
        "PYLAV__EXTERNAL_UNMANAGED_PORT": EXTERNAL_UNMANAGED_PORT,
        "PYLAV__EXTERNAL_UNMANAGED_PASSWORD": EXTERNAL_UNMANAGED_PASSWORD,
        "PYLAV__EXTERNAL_UNMANAGED_SSL": EXTERNAL_UNMANAGED_SSL,
        "PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS": TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS,
        "PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS": TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS,
        "PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS": TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS,
    }
    with ENV_FILE.open(mode="w") as file:
        LOGGER.debug("Creating %s with the following content: %r", ENV_FILE, data)
        yaml.safe_dump(data, file, default_flow_style=False, sort_keys=False, encoding="utf-8")

else:
    LOGGER.info("%s exist - Environment variables will be read from it.", ENV_FILE)
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

        if (REDIS_FULL_ADDRESS_RESPONSE_CACHE := data.get("PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE")) is None:
            REDIS_FULL_ADDRESS_RESPONSE_CACHE = os.getenv("PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE")
            data_new["PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE"] = REDIS_FULL_ADDRESS_RESPONSE_CACHE

        if (LINKED_BOT_IDS := data.get("PYLAV__LINKED_BOT_IDS")) is None:
            LINKED_BOT_IDS = list(map(str.strip, os.getenv("PYLAV__LINKED_BOT_IDS", "").split("|")))
            data_new["PYLAV__LINKED_BOT_IDS"] = LINKED_BOT_IDS

        if (USE_BUNDLED_EXTERNAL_NODES := data.get("PYLAV__USE_BUNDLED_EXTERNAL_NODES")) is None:
            USE_BUNDLED_EXTERNAL_NODES = bool(int(os.getenv("PYLAV__USE_BUNDLED_EXTERNAL_NODES", "1")))
            data_new["PYLAV__USE_BUNDLED_EXTERNAL_NODES"] = USE_BUNDLED_EXTERNAL_NODES

        if (JAVA_EXECUTABLE := data.get("PYLAV__JAVA_EXECUTABLE")) is None:
            JAVA_EXECUTABLE = os.getenv("PYLAV__JAVA_EXECUTABLE", "java")
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

        if (TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS := data.get("PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS")) is None:
            TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS = max(
                int(os.getenv("PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS", "1")), 1
            )
            data_new["PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS"] = TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS

        if (
            TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS := data.get(
                "PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS"
            )
        ) is None:
            TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS = max(
                int(os.getenv("PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS", "7")), 7
            )
            data_new[
                "PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS"
            ] = TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS

        if (TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS := data.get("PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS")) is None:
            TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS = max(
                int(os.getenv("PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS", "7")), 7
            )
            data_new["PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS"] = TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS

    if DeepDiff(data, data_new, ignore_order=True):
        with ENV_FILE.open(mode="w") as file:
            LOGGER.info("Updating %s with the following content: %r", ENV_FILE, data_new)
            yaml.safe_dump(data_new, file, default_flow_style=False, sort_keys=False, encoding="utf-8")
