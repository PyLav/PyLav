from __future__ import annotations

import importlib.metadata
import typing

from packaging.version import Version, parse

__version__: str = importlib.metadata.version("Py-Lav")
VERSION: Version = typing.cast(Version, parse(__version__))
__PATH = None if (__PATHS := importlib.metadata.files("Py-Lav")) is None else next(iter(__PATHS), None)
LOCATION = __PATH.locate() if __PATH else None


__all__ = (
    "__version__",
    "VERSION",
    "LOCATION",
)
