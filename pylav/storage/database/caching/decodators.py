from __future__ import annotations

import functools
from typing import Callable

from pylav.storage.database.caching.cache import CACHE
from pylav.storage.database.caching.functions import key_builder


def maybe_cached(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await CACHE(ttl=None, key=key_builder(func, *args, **kwargs))(func)(*args, **kwargs)

    return wrapper
