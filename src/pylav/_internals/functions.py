import pathlib
from typing import TypeVar

T = TypeVar("T")


def _get_path(path: T | pathlib.Path) -> str | T | None:
    from pylav.utils import get_true_path

    return get_true_path(path, fallback=path)
