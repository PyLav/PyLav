from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable

from pylav.constants.config import READ_CACHING_ENABLED
from pylav.storage.database.cache.cache import CACHE
from pylav.storage.database.cache.functions import key_builder
from pylav.type_hints.generics import ANY_GENERIC_TYPE, PARAM_SPEC_TYPE


def maybe_cached(
    func: Callable[PARAM_SPEC_TYPE, Awaitable[ANY_GENERIC_TYPE]]  # type: ignore
) -> Callable[ANY_GENERIC_TYPE, Awaitable[ANY_GENERIC_TYPE]]:  # type: ignore
    @functools.wraps(func)
    async def wrapper(*args: PARAM_SPEC_TYPE.args, **kwargs: PARAM_SPEC_TYPE.kwargs) -> Awaitable[ANY_GENERIC_TYPE]:
        if READ_CACHING_ENABLED:
            return await CACHE(ttl=None, key=key_builder(func, *args, **kwargs))(func)(*args, **kwargs)
        return await func(*args, **kwargs)

    return wrapper
