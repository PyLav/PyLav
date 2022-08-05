from __future__ import annotations

import os
import pathlib

import yaml
from deepdiff import DeepDiff

from pylav._logging import getLogger

LOGGER = getLogger("PyLav.Enviroment")

ENV_FILE = pathlib.Path.home() / "pylav.yaml"

if not ENV_FILE.exists():
    LOGGER.warning(
        "%s does not exist - This is not a problem if it does then the enviroment variables will be read from it.",
        ENV_FILE,
    )
    POSTGRE_PORT = os.getenv("PYLAV__POSTGRES_PORT", os.getenv("PGPORT"))
    POSTGRE_PASSWORD = os.getenv("PYLAV__POSTGRES_PASSWORD", os.getenv("PGPASSWORD"))
    POSTGRE_USER = os.getenv("PYLAV__POSTGRES_USER", os.getenv("PGUSER"))
    POSTGRE_DATABASE = os.getenv("PYLAV__POSTGRES_DB", os.getenv("PGDATABASE"))
    POSTGRE_HOST = os.getenv("PYLAV__POSTGRES_HOST", os.getenv("PGHOST"))

    JAVA_EXECUTABLE = os.getenv("PYLAV__JAVA_EXECUTABLE", "java")
    LINKED_BOT_IDS = list(map(str.strip, os.getenv("PYLAV__JAVA_EXECUTABLE", "").split("|")))
    USE_BUNDLED_EXTERNAL_NODES = bool(int(os.getenv("PYLAV__USE_BUNDLED_EXTERNAL_NODES", "1")))

    REDIS_FULLADDRESS_RESPONSE_CACHE = os.getenv("PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE")

    EXTERNAL_UNMANAGED_HOST = os.getenv("PYLAV__EXTERNAL_UNMANAGED_HOST")
    EXTERNAL_UNMANAGED_PORT = int(os.getenv("PYLAV__EXTERNAL_UNMANAGED_PORT", "80"))
    EXTERNAL_UNMANAGED_PASSWORD = os.getenv("PYLAV__EXTERNAL_UNMANAGED_PASSWORD")
    EXTERNAL_UNMANAGED_SSL = bool(int(os.getenv("PYLAV__EXTERNAL_UNMANAGED_SSL", 0)))
    data = {
        "PYLAV__POSTGRES_PORT": POSTGRE_PORT,
        "PYLAV__POSTGRES_PASSWORD": POSTGRE_PASSWORD,
        "PYLAV__POSTGRES_USER": POSTGRE_USER,
        "PYLAV__POSTGRES_DB": POSTGRE_DATABASE,
        "PYLAV__POSTGRES_HOST": POSTGRE_HOST,
        "PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE": REDIS_FULLADDRESS_RESPONSE_CACHE,
        "PYLAV__JAVA_EXECUTABLE": JAVA_EXECUTABLE,
        "PYLAV__LINKED_BOT_IDS": LINKED_BOT_IDS,
        "PYLAV__USE_BUNDLED_EXTERNAL_NODES": USE_BUNDLED_EXTERNAL_NODES,
        "PYLAV__EXTERNAL_UNMANAGED_HOST": EXTERNAL_UNMANAGED_HOST,
        "PYLAV__EXTERNAL_UNMANAGED_PORT": EXTERNAL_UNMANAGED_PORT,
        "PYLAV__EXTERNAL_UNMANAGED_PASSWORD": EXTERNAL_UNMANAGED_PASSWORD,
        "PYLAV__EXTERNAL_UNMANAGED_SSL": EXTERNAL_UNMANAGED_SSL,
    }
    with ENV_FILE.open(mode="w") as file:
        LOGGER.debug("Creating %s with the following content: %r", ENV_FILE, data)
        yaml.safe_dump(data, file, default_flow_style=False, sort_keys=False, encoding="utf-8")

else:
    LOGGER.warning("%s exist - Enviroment variables will be read from it.", ENV_FILE)
    with ENV_FILE.open(mode="r") as file:
        data = yaml.safe_load(file.read())

        POSTGRE_PORT = data.get("PYLAV__POSTGRES_PORT", os.getenv("PYLAV__POSTGRES_PORT", os.getenv("PGPORT")))
        POSTGRE_PASSWORD = data.get(
            "PYLAV__POSTGRES_PASSWORD", os.getenv("PYLAV__POSTGRES_PASSWORD", os.getenv("PGPASSWORD"))
        )
        POSTGRE_USER = data.get("PYLAV__POSTGRES_USER", os.getenv("PYLAV__POSTGRES_USER", os.getenv("PGUSER")))
        POSTGRE_DATABASE = data.get("PYLAV__POSTGRES_DB", os.getenv("PYLAV__POSTGRES_DB", os.getenv("PGDATABASE")))
        POSTGRE_HOST = data.get(
            " PYLAV__POSTGRES_HOST", os.getenv("PYLAV__POSTGRES_HOST", os.getenv("PYLAV__POSTGRES_HOST"))
        )
        REDIS_FULLADDRESS_RESPONSE_CACHE = data.get(
            "PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE", os.getenv("PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE")
        )
        JAVA_EXECUTABLE = data.get("PYLAV__JAVA_EXECUTABLE", os.getenv("PYLAV__JAVA_EXECUTABLE", "java"))
        LINKED_BOT_IDS = data.get(
            "PYLAV__LINKED_BOT_IDS", list(map(str.strip, os.getenv("PYLAV__JAVA_EXECUTABLE", "")))
        )
        USE_BUNDLED_EXTERNAL_NODES = data.get(
            "PYLAV__USE_BUNDLED_EXTERNAL_NODES", bool(int(os.getenv("PYLAV__USE_BUNDLED_EXTERNAL_NODES", "1")))
        )
        EXTERNAL_UNMANAGED_HOST = data.get(
            "PYLAV__EXTERNAL_UNMANAGED_HOST", os.getenv("PYLAV__EXTERNAL_UNMANAGED_HOST")
        )
        EXTERNAL_UNMANAGED_PORT = int(
            data.get("PYLAV__EXTERNAL_UNMANAGED_PORT", os.getenv("PYLAV__EXTERNAL_UNMANAGED_PORT", "80"))
        )
        EXTERNAL_UNMANAGED_PASSWORD = data.get(
            "PYLAV__EXTERNAL_UNMANAGED_PASSWORD", os.getenv("PYLAV__EXTERNAL_UNMANAGED_PASSWORD")
        )
        EXTERNAL_UNMANAGED_SSL = data.get(
            "PYLAV__EXTERNAL_UNMANAGED_SSL", bool(int(os.getenv("PYLAV__EXTERNAL_UNMANAGED_SSL", "0")))
        )

    data_new = {
        "PYLAV__POSTGRES_PORT": POSTGRE_PORT,
        "PYLAV__POSTGRES_PASSWORD": POSTGRE_PASSWORD,
        "PYLAV__POSTGRES_USER": POSTGRE_USER,
        "PYLAV__POSTGRES_DB": POSTGRE_DATABASE,
        "PYLAV__POSTGRES_HOST": POSTGRE_HOST,
        "PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE": REDIS_FULLADDRESS_RESPONSE_CACHE,
        "PYLAV__JAVA_EXECUTABLE": JAVA_EXECUTABLE,
        "PYLAV__LINKED_BOT_IDS": LINKED_BOT_IDS,
        "PYLAV__USE_BUNDLED_EXTERNAL_NODES": USE_BUNDLED_EXTERNAL_NODES,
        "PYLAV__EXTERNAL_UNMANAGED_HOST": EXTERNAL_UNMANAGED_HOST,
        "PYLAV__EXTERNAL_UNMANAGED_PORT": EXTERNAL_UNMANAGED_PORT,
        "PYLAV__EXTERNAL_UNMANAGED_PASSWORD": EXTERNAL_UNMANAGED_PASSWORD,
        "PYLAV__EXTERNAL_UNMANAGED_SSL": EXTERNAL_UNMANAGED_SSL,
    }
    if DeepDiff(data, data_new, ignore_order=True):
        with ENV_FILE.open(mode="w") as file:
            LOGGER.debug("Updating %s with the following content: %r", ENV_FILE, data_new)
            yaml.safe_dump(data_new, file, default_flow_style=False, sort_keys=False, encoding="utf-8")
