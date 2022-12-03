import os
import pathlib

from pylav._internals.pylav_yaml_builder import build_from_envvars
from pylav.logging import getLogger

LOGGER = getLogger("PyLav.Environment")

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
