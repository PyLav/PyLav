from __future__ import annotations

import sys

if sys.version_info >= (3, 10):
    from pylav.vendored.aiopath import aiopath_310 as aiopath
else:
    import aiopath as aiopath

__all__ = ("aiopath",)
