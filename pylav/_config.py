from __future__ import annotations

import os
import pathlib
import sys

import platformdirs

from pylav.vendored import aiopath

basic_config: dict = {}
instance_name = None

appdir = platformdirs.PlatformDirs("PyLav")
__CONFIG_DIR = pathlib.Path(appdir.user_config_path)
_system_user = sys.platform == "linux" and 0 < os.getuid() < 1000
if _system_user:
    __CONFIG_DIR = pathlib.Path(appdir.site_data_path)
__CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR = aiopath.AsyncPath(__CONFIG_DIR)


def update_event_loop_policy():
    if sys.implementation.name == "cpython":
        # Let's not force this dependency, uvloop is much faster on cpython
        try:
            import uvloop
        except ImportError:
            pass
        else:
            import asyncio

            if not isinstance(asyncio.get_event_loop_policy(), uvloop.EventLoopPolicy):
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
