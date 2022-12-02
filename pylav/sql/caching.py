import functools
import inspect
import typing
from collections.abc import Iterable, Iterator
from typing import Any, Callable

from cashews import Cache

from pylav._logging import getLogger
from pylav.envvars import READ_CACHING_ENABLED
from pylav.utils import _LOCK, _synchronized

LOGGER = getLogger("PyLav.Caching")

if READ_CACHING_ENABLED:
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


CACHE = Cache("ReadCache")
CACHE.setup("mem://?check_interval=10&size=10000", enable=READ_CACHING_ENABLED)


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


def maybe_cached(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await CACHE(ttl=None, key=key_builder(func, *args, **kwargs))(func)(*args, **kwargs)

    return wrapper


async def invalidate_cache(method: Callable, instance: object):
    await CACHE.delete(key=key_builder(method, instance))  # type: ignore


async def update_cache(method: Callable, instance: object, value: Any):
    await CACHE.set(key=key_builder(method, instance), value=value)  # type: ignore


async def update_cache_multi(pairs: Iterable[tuple[Callable, Any]], instance: object):
    await CACHE.set_many(pairs={key_builder(method, instance): value for method, value in pairs})


async def invalidate_cache_multi(methods: Iterable[Callable], instance: object):
    await CACHE.delete_many(*[key_builder(method, instance) for method in methods])


class CachedModel:
    @staticmethod
    def _predicate(member: typing.Callable) -> bool:
        """Check if the method is a cached method"""
        if getattr(member, "__name__", "_").startswith("_"):
            return False
        return bool(hasattr(member, "cache")) if inspect.ismethod(member) else False

    def get_all_methods(self) -> Iterator[typing.Callable]:
        """Get all methods of the class"""

        return [_callable for member, _callable in inspect.getmembers(self, predicate=self._predicate)]

    async def invalidate_cache(self, *methods: typing.Callable) -> None:
        """Invalidate the cache for the given methods if not specify all"""
        if methods:
            await invalidate_cache_multi(methods, self)
        else:
            await invalidate_cache_multi(self.get_all_methods(), self)  # type: ignore

    async def update_cache(self, *pairs: tuple[typing.Callable, typing.Any]) -> None:
        """Update the cache for the specified method"""
        await update_cache_multi(pairs, self)
