import os
import pathlib
import sys

import aiopath
import platformdirs

from pylav._internals.pylav_yaml_builder import build_from_envvars
from pylav.logging import getLogger

LOGGER = getLogger("PyLav.Environment")

BASIC_CONFIG = {}
INSTANCE_NAME = None

APPDIR = platformdirs.PlatformDirs("PyLav")
__CONFIG_DIR = pathlib.Path(APPDIR.user_config_path)
_system_user = sys.platform == "linux" and 0 < os.getuid() < 1000
if _system_user:
    __CONFIG_DIR = pathlib.Path(APPDIR.site_data_path)
__CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR = aiopath.AsyncPath(__CONFIG_DIR)


if full_path := os.getenv("PYLAV__YAML_CONFIG"):
    ENV_FILE = pathlib.Path(full_path)
else:
    ENV_FILE = pathlib.Path.home() / "pylav.yaml"


if not ENV_FILE.exists():
    LOGGER.warning(
        "%s does not exist - This is not a problem if it does then the environment variables will be read from it",
        ENV_FILE,
    )
    build_from_envvars()
else:
    LOGGER.info("%s exist - Environment variables will be read from it", ENV_FILE)
