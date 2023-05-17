from __future__ import annotations

import contextlib
import inspect
import os
import pathlib
import shutil
import sys
from collections.abc import Callable, Iterator
from typing import TypeVar, get_type_hints

from pylav.type_hints.generics import ANY_GENERIC_TYPE, PARAM_SPEC_TYPE

T = TypeVar("T")


def _get_path(path: T | pathlib.Path) -> str | T | None:
    return get_true_path(path, fallback=path)


def update_event_loop_policy() -> None:
    if sys.implementation.name == "cpython":
        # Let's not force this dependency, uvloop is much faster on cpython
        try:
            import uvloop  # type: ignore
        except ImportError:
            pass
        else:
            import asyncio

            if not isinstance(asyncio.get_event_loop_policy(), uvloop.EventLoopPolicy):
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def check_annotated(
    func: Callable[PARAM_SPEC_TYPE, ANY_GENERIC_TYPE]  # type: ignore
) -> Callable[PARAM_SPEC_TYPE, ANY_GENERIC_TYPE]:  # type: ignore
    hints = get_type_hints(func, include_extras=True)
    spec = inspect.getfullargspec(func)

    def wrapper(*args: PARAM_SPEC_TYPE.args, **kwargs: PARAM_SPEC_TYPE.kwargs) -> ANY_GENERIC_TYPE:
        for idx, arg_name in enumerate(spec[0]):
            hint = hints.get(arg_name)
            validators = getattr(hint, "__metadata__", None)
            if not validators:
                continue
            for validator in validators:
                validator.validate_value(args[idx])

        return func(*args, **kwargs)

    return wrapper


def add_property(inst: object, name: str, method: Callable) -> None:
    cls = type(inst)
    if not hasattr(cls, "__per_instance"):
        cls = type(cls.__name__, (cls,), {})
        cls.__per_instance = True
        inst.__class__ = cls
    setattr(cls, name, property(method))


def get_true_path(executable: str, fallback: ANY_GENERIC_TYPE = None) -> str | ANY_GENERIC_TYPE | None:
    """Returns the true path of the executable."""

    path = os.environ.get("JAVA_HOME", executable)
    with add_env_path(path if os.path.isdir(path) else os.path.split(path)[0]) as path_string:
        executable = shutil.which(executable, path=path_string)
    return executable or fallback


@contextlib.contextmanager
def add_env_path(path: str | os.PathLike) -> Iterator[str]:
    """Adds a path to the environment path temporarily."""
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


def fix(string: str, data, *, e: bool = False) -> str | bytes:
    index_list, rem = data
    new_string = string[rem : -1 * rem]
    res = ""
    for idx in range(0, len(new_string)):
        # checking for index list for uppercase
        if idx in index_list:
            res += new_string[idx].upper()
        else:
            res += new_string[idx]
    res += "=="
    final = res
    return final.encode() if e else final
