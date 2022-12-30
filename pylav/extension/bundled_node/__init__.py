from __future__ import annotations

import pathlib
from typing import Final

import aiopath

from pylav.constants.config import CONFIG_DIR
from pylav.logging import getLogger

LOGGER = getLogger("PyLav.ManagedNode")

LAVALINK_DOWNLOAD_DIR = CONFIG_DIR / "lavalink"
_LAVALINK_DOWNLOAD_DIR = pathlib.Path(LAVALINK_DOWNLOAD_DIR)  # type: ignore
_LAVALINK_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
_LAVALINK_JAR_FILE_FORCED_SYNC = _LAVALINK_DOWNLOAD_DIR / "forced.jar"

LAVALINK_DOWNLOAD_DIR: aiopath.AsyncPath = aiopath.AsyncPath(LAVALINK_DOWNLOAD_DIR)
LAVALINK_JAR_FILE: aiopath.AsyncPath = LAVALINK_DOWNLOAD_DIR / "Lavalink.jar"
LAVALINK_JAR_FILE_FORCED: Final[aiopath.AsyncPath] = LAVALINK_DOWNLOAD_DIR / "forced.jar"
LAVALINK_APP_YML: Final[aiopath.AsyncPath] = LAVALINK_DOWNLOAD_DIR / "application.yml"
if USING_FORCED := _LAVALINK_JAR_FILE_FORCED_SYNC.exists():
    LOGGER.warning("%s found, disabling any JAR automated downloads", LAVALINK_JAR_FILE_FORCED)
    LAVALINK_JAR_FILE: aiopath.AsyncPath = LAVALINK_JAR_FILE_FORCED
