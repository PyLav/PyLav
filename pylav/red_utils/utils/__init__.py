from __future__ import annotations

import functools
import hashlib
from collections.abc import MutableMapping
from typing import Any

__all__ = ("decorators", "rgetattr", "rsetattr")


def rsetattr(obj: object, attr: str, val: Any) -> None:
    pre, _, post = attr.rpartition(".")
    setattr(rgetattr(obj, pre) if pre else obj, post, val)


def rgetattr(obj: object, attr: str, *args: Any) -> Any:
    def _getattr(obj2, attr2):
        return getattr(obj2, attr2, *args)

    return functools.reduce(_getattr, [obj] + attr.split("."))


def recursive_merge(d1: dict, d2: dict) -> dict:
    """
    Update two dicts of dicts recursively,
    if either mapping has leaves that are non-dicts,
    the second's leaf overwrites the first's.
    """
    for k, v in d1.items():
        if k in d2 and all(isinstance(e, MutableMapping) for e in (v, d2[k])):
            d2[k] = recursive_merge(v, d2[k])
    return d1 | d2


class Mutator:
    def __init__(self, obj: object):  # sourcery skip: remove-unnecessary-cast
        self.obj = obj
        self.name = obj.name if hasattr(obj, "name") else str(obj.__class__.__name__)
        if hasattr(obj, "id"):
            self.id = str(obj.id)
        else:
            i = hashlib.md5()
            i.update(self.name.encode())
            i.update(str(id(obj)).encode())
            self.id = str(int(i.hexdigest(), 16))[:16]
