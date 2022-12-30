from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from pylav.storage.database.cache.cache import CACHE


def key_builder(method: Callable, *args: Any, **kwargs: Any) -> str:  # noqa
    return f"{method.__module__}:{args[0].__class__.__name__}:{method.__name__}:{args[0].get_cache_key()}"  # noqa


async def invalidate_cache(method: Callable, instance: object) -> None:
    await CACHE.delete(key=key_builder(method, instance))


async def update_cache(method: Callable, instance: object, value: Any) -> None:
    await CACHE.set(key=key_builder(method, instance), value=value)


async def update_cache_multi(pairs: Iterable[tuple[Callable, Any]], instance: object) -> None:
    await CACHE.set_many(pairs={key_builder(method, instance): value for method, value in pairs})


async def invalidate_cache_multi(methods: Iterable[Callable], instance: object) -> None:
    await CACHE.delete_many(*[key_builder(method, instance) for method in methods])
