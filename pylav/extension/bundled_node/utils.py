from __future__ import annotations

import math
import platform
import sys

import psutil

from pylav._internals.functions import get_true_path
from pylav.type_hints.dict_typing import JSON_DICT_TYPE


def get_max_allocation_size(executable: str) -> tuple[int, bool]:
    """Returns the maximum heap size allowed for the given executable."""
    if platform.architecture(executable)[0] == "64bit":
        max_heap_allowed = psutil.virtual_memory().total
        thinks_is_64_bit = True
    else:
        max_heap_allowed = min(4 * 1024**3, psutil.virtual_memory().total)
        thinks_is_64_bit = False
    return max_heap_allowed, thinks_is_64_bit


def _calculate_ram(max_allocation: int) -> tuple[str, str, int, int]:
    min_ram_int = 64 * 1024**2
    _min_max = 512 * 1024**2
    max_ram_allowed = max(max_allocation * 0.5, _min_max)
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
    """Returns the default ram for the jar"""
    # We don't know the java executable at this stage - not worth the extra work required here
    max_allocation, __ = get_max_allocation_size(sys.executable)
    min_ram, max_ram, min_ram_int, max_ram_int = _calculate_ram(max_allocation)
    return min_ram, max_ram, min_ram_int, max_ram_int


def get_jar_ram_actual(executable: str) -> tuple[str, str, int, int]:
    """Returns the actual ram for the jar"""
    if not executable:
        from pylav.constants.config import JAVA_EXECUTABLE

        executable = JAVA_EXECUTABLE
    executable = get_true_path(executable, sys.executable)
    max_allocation, __ = get_max_allocation_size(executable)
    min_ram, max_ram, min_ram_int, max_ram_int = _calculate_ram(max_allocation)
    return min_ram, max_ram, min_ram_int, max_ram_int


def convert_function(key: str) -> str:
    """Converts a key to a valid key."""
    return key.replace("_", "-")


def change_dict_naming_convention(data: JSON_DICT_TYPE) -> JSON_DICT_TYPE:
    """Changes the naming convention of a dict."""
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
