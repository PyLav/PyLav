from __future__ import annotations

import importlib.metadata
import typing

from packaging.version import Version, parse

from pylav.__version__ import __version__ as __version__

try:
    __PATH = None if (__PATHS := importlib.metadata.files("Py-Lav")) is None else next(iter(__PATHS), None)
except importlib.metadata.PackageNotFoundError:
    __PATH = None
VERSION: Version = typing.cast(Version, parse(__version__))
LOCATION = __PATH.locate() if __PATH else None


__all__ = (
    "__version__",
    "VERSION",
    "LOCATION",
)
