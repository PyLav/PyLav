from __future__ import annotations

import contextlib
import math
import os
import platform
import shutil
import sys
from collections.abc import Iterator

import psutil

from pylav.type_hints.dict_typing import JSON_DICT_TYPE
from pylav.type_hints.generics import ANY_GENERIC_TYPE


def get_max_allocation_size(executable: str) -> tuple[int, bool]:
    if platform.architecture(executable)[0] == "64bit":
        max_heap_allowed = psutil.virtual_memory().total
        thinks_is_64_bit = True
    else:
        max_heap_allowed = 4 * 1024**3
        thinks_is_64_bit = False
    return max_heap_allowed, thinks_is_64_bit


def _calculate_ram(max_allocation: int, is_64bit: bool) -> tuple[str, str, int, int]:
    min_ram_int = 64 * 1024**2
    max_ram_allowed = max_allocation * 0.5 if is_64bit else max_allocation
    max_ram_int = max(min_ram_int, max_ram_allowed)
    size_name = ("", "K", "M", "G", "T")
    i = int(math.floor(math.log(min_ram_int, 1024)))
    p = math.pow(1024, i)
    s = int(min_ram_int // p)
    min_ram = f"{s}{size_name[i]}"

    i = int(math.floor(math.log(max_ram_int, 1024)))
    p = math.pow(1024, i)
    s = int(max_ram_int // p)
    max_ram = f"{s}{size_name[i]}"

    return min_ram, max_ram, min_ram_int, max_ram_int


def get_jar_ram_defaults() -> tuple[str, str, int, int]:
    # We don't know the java executable at this stage - not worth the extra work required here
    max_allocation, is_64bit = get_max_allocation_size(sys.executable)
    min_ram, max_ram, min_ram_int, max_ram_int = _calculate_ram(max_allocation, is_64bit)
    return min_ram, max_ram, min_ram_int, max_ram_int


def get_jar_ram_actual(executable: str) -> tuple[str, str, int, int]:
    if not executable:
        from pylav.constants.config import JAVA_EXECUTABLE

        executable = JAVA_EXECUTABLE
    executable = get_true_path(executable, sys.executable)
    max_allocation, is_64bit = get_max_allocation_size(executable)
    min_ram, max_ram, min_ram_int, max_ram_int = _calculate_ram(max_allocation, is_64bit)
    return min_ram, max_ram, min_ram_int, max_ram_int


def get_true_path(executable: str, fallback: ANY_GENERIC_TYPE = None) -> str | ANY_GENERIC_TYPE | None:
    path = os.environ.get("JAVA_HOME", executable)
    with add_env_path(path if os.path.isdir(path) else os.path.split(path)[0]) as path_string:
        executable = shutil.which(executable, path=path_string)
    return executable or fallback


@contextlib.contextmanager
def add_env_path(path: str | os.PathLike) -> Iterator[str]:
    path = os.fspath(path)
    existing_path = "PATH" in os.environ
    old_path = os.environ["PATH"] if existing_path else None
    try:
        if path not in os.environ["PATH"]:
            yield path + os.pathsep + os.environ["PATH"]
        else:
            yield os.environ["PATH"]
    finally:
        if existing_path:
            os.environ["PATH"] = old_path
        else:
            del os.environ["PATH"]


def convert_function(key: str) -> str:
    return key.replace("_", "-")


def change_dict_naming_convention(data: JSON_DICT_TYPE) -> JSON_DICT_TYPE:
    new = {}
    for k, v in data.items():
        new_v = v
        if isinstance(v, dict):
            new_v = change_dict_naming_convention(v)
        elif isinstance(v, list):
            new_v = []
            for x in v:
                if isinstance(x, dict):
                    new_v.append(change_dict_naming_convention(x))
                else:
                    new_v.append(x)
        new[convert_function(k)] = new_v
    return new
