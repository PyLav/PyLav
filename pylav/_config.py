from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import appdirs
from redbot.core.data_manager import cog_data_path as red_cog_data_path

basic_config: dict = {}
instance_name = None

appdir = appdirs.AppDirs("Red-DiscordBot")
config_dir = Path(appdir.user_config_dir)
_system_user = sys.platform == "linux" and 0 < os.getuid() < 1000
if _system_user:
    if Path.home().exists():
        # We don't want to break someone just because they created home dir
        # but were already using the site_data_dir.
        #
        # But otherwise, we do want Red to use user_config_dir if home dir exists.
        _maybe_config_file = Path(appdir.site_data_dir) / "config.json"
        if _maybe_config_file.exists():
            config_dir = _maybe_config_file.parent
    else:
        config_dir = Path(appdir.site_data_dir)

config_file = config_dir / "config.json"


def load_basic_configuration():
    global basic_config
    global instance_name
    try:
        with config_file.open(encoding="utf-8") as fs:
            config = json.load(fs)
        instance_name = list(config.keys())[-1]
        basic_config = config[instance_name]
    except (FileNotFoundError, KeyError):
        basic_config["DATA_PATH"] = config_dir.resolve()


def _base_data_path() -> Path:
    if not basic_config:
        raise RuntimeError("You must load the basic config before you can get the base data path.")
    path = basic_config["DATA_PATH"]
    return Path(path).resolve()


def cog_data_path(raw_name: str = None) -> Path:
    try:
        base_data_path = Path(_base_data_path())
    except RuntimeError:
        load_basic_configuration()
        base_data_path = Path(_base_data_path())
    cog_path = base_data_path / "cogs"

    if raw_name is not None:
        cog_path = cog_path / raw_name
    cog_path.mkdir(exist_ok=True, parents=True)

    return cog_path.resolve()


try:
    LIB_CONFIG_FOLDER = red_cog_data_path(raw_name="PyLav")
except RuntimeError:
    LIB_CONFIG_FOLDER = cog_data_path(raw_name="PyLav")

__VERSION__ = "0.0.1"
