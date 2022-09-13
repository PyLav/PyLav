import functools
import inspect
import typing
from collections.abc import Iterable, Iterator
from typing import Any, Callable

from aiocache import Cache, cached

from pylav._logging import getLogger
from pylav.envvars import CACHING_ENABLED
from pylav.utils import _LOCK, _synchronized

LOGGER = getLogger("PyLav.Caching")

if CACHING_ENABLED:
    LOGGER.warning(
        "Caching is enabled, "
        "this will make it so live edits to the database will not be reflected "
        "in the bot until the cache is invalidated or bot is restarted."
    )
else:
    LOGGER.info(
        "Caching is disabled, "
        "this will make it so live edits to the database will be reflected in the bot immediately."
    )


class _SingletonByKey(type):
    _instances = {}

    @classmethod
    def _get_key(cls, mro, **kwargs):
        singleton_key = f'{kwargs.get("id")}'
        for base in mro:
            if base.__module__.startswith("pylav.sql.models"):
                key_name = base.__name__
                if "LibConfigModel" in key_name:
                    singleton_key += f".{kwargs.get('bot')}"
                return singleton_key, key_name

    def __call__(cls, *args, **kwargs):
        # sourcery skip: instance-method-first-arg-name
        key = cls._get_key(cls.mro(), **kwargs)
        if key not in cls._instances:
            cls._locked_call(*args, **kwargs)
        return cls._instances[key]

    @_synchronized(_LOCK)
    def _locked_call(cls, *args, **kwargs):
        key = cls._get_key(cls.mro(), **kwargs)
        if key not in cls._instances:
            singleton = super().__call__(*args, **kwargs)
            cls._instances[key] = singleton


def key_builder(method: Callable, *args: Any, **kwargs: Any) -> str:
    if "LibConfigModel" in args[0].__class__.__name__:
        _id = args[0].bot
    else:
        _id = args[0].id
    return f"{f'{method.__module__}'}.{args[0].__class__.__name__}.{method.__name__}.{_id}"


CACHE = cached(ttl=None, cache=Cache.MEMORY, key_builder=key_builder)


def maybe_cached(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await CACHE(func)(*args, **kwargs) if CACHING_ENABLED else await func(*args, **kwargs)

    return wrapper


async def invalidate_cache(method: Callable, instance: object):
    if CACHING_ENABLED:
        await CACHE.cache.delete(key_builder(method, instance))  # type: ignore


async def update_cache(method: Callable, instance: object, value: Any):
    if CACHING_ENABLED:
        await CACHE.cache.set(key_builder(method, instance), value)  # type: ignore


async def update_cache_multi(pairs: Iterable[tuple[Callable, Any]], instance: object):
    if CACHING_ENABLED:
        await CACHE.cache.multi_set([(key_builder(method, instance), value) for method, value in pairs])  # type: ignore


async def invalidate_cache_multi(methods: Iterable[Callable], instance: object):
    if CACHING_ENABLED:
        for method in methods:
            await CACHE.cache.delete(key_builder(method, instance))


class CachedModel:
    def _predicate(self, member: typing.Callable) -> bool:
        """Check if the method is a cached method"""
        if member.__name__.startswith("_"):
            return False
        return bool(hasattr(member, "cache")) if inspect.ismethod(member) else False

    def get_all_methods(self) -> Iterator[typing.Callable]:
        """Get all methods of the class"""

        return [_callable for member, _callable in inspect.getmembers(self, predicate=self._predicate)]

    async def invalidate_cache(self, *methods: typing.Callable) -> None:
        """Invalidate the cache for the given methods if not specify all"""
        if not CACHING_ENABLED:
            return
        if methods:
            await invalidate_cache_multi(methods, self)
        else:
            await invalidate_cache_multi(self.get_all_methods(), self)  # type: ignore

    async def update_cache(self, *pairs: tuple[typing.Callable, typing.Any]) -> None:
        """Update the cache for the specified method"""
        if not CACHING_ENABLED:
            return
        await update_cache_multi(pairs, self)
