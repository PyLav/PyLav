from __future__ import annotations

import typing

import importlib_metadata
from packaging.version import Version, parse

from pylav.__version__ import __version__ as __version__

VERSION: Version = typing.cast(Version, parse(__version__))
__PATH = None if (__PATHS := importlib_metadata.files("Py-Lav")) is None else next(iter(__PATHS), None)
LOCATION = __PATH.locate() if __PATH else None


__all__ = (
    "__version__",
    "VERSION",
    "LOCATION",
)
