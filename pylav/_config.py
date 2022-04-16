from __future__ import annotations

import os
import sys
from pathlib import Path

import appdirs

basic_config: dict = {}
instance_name = None

appdir = appdirs.AppDirs("PyLav")
CONFIG_DIR = Path(appdir.user_data_dir)
_system_user = sys.platform == "linux" and 0 < os.getuid() < 1000
if _system_user:
    CONFIG_DIR = Path(appdir.site_data_dir)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
__VERSION__ = "0.0.1"
