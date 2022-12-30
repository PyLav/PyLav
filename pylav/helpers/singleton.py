from __future__ import annotations

import asyncio
import functools
import threading
from collections.abc import Awaitable, Callable
from typing import Any

from pylav.type_hints.generics import ANY_GENERIC_TYPE, PARAM_SPEC_TYPE

_LOCK_SINGLETON_CLASS = threading.Lock()
_LOCK_SINGLETON_CALLABLE = threading.Lock()
_LOCK_SINGLETON_CACHE_CALLABLE = threading.Lock()


def synchronized_method_call(
    lock: threading.Lock, discard: bool = False
) -> Callable[PARAM_SPEC_TYPE, ANY_GENERIC_TYPE]:  # type: ignore
    """Synchronization decorator"""

    def wrapper(
        f: Callable[PARAM_SPEC_TYPE, ANY_GENERIC_TYPE]  # type: ignore
    ) -> Callable[PARAM_SPEC_TYPE, ANY_GENERIC_TYPE]:  # type: ignore
        @functools.wraps(f)
        def inner_wrapper(
            *args: PARAM_SPEC_TYPE.args, **kwargs: PARAM_SPEC_TYPE.kwargs
        ) -> ANY_GENERIC_TYPE | Awaitable[ANY_GENERIC_TYPE] | None:
            if lock.locked() and discard:
                return
            with lock:
                return f(*args, **kwargs)

        return inner_wrapper

    return wrapper


class SingletonClass(type):
    _instances = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> SingletonClass:
        # sourcery skip: instance-method-first-arg-name
        if cls not in cls._instances:
            cls._locked_call(*args, **kwargs)
        return cls._instances[cls]

    @synchronized_method_call(_LOCK_SINGLETON_CLASS)
    def _locked_call(cls, *args: Any, **kwargs: Any) -> None:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)


class SingletonCallable:
    _has_run = {}
    _responses = {}

    @classmethod
    @synchronized_method_call(_LOCK_SINGLETON_CALLABLE)
    def reset(cls) -> None:
        cls._has_run = {}
        cls._responses = {}

    @classmethod
    @synchronized_method_call(_LOCK_SINGLETON_CALLABLE)
    def run_once(
        cls, f: Callable[PARAM_SPEC_TYPE, ANY_GENERIC_TYPE]  # type: ignore
    ) -> Callable[PARAM_SPEC_TYPE, ANY_GENERIC_TYPE]:  # type: ignore
        @functools.wraps(f)
        def wrapper(*args: PARAM_SPEC_TYPE.args, **kwargs: PARAM_SPEC_TYPE.kwargs) -> ANY_GENERIC_TYPE:
            if not cls._has_run.get(f, False):
                cls._has_run[f] = True
                output = f(*args, **kwargs)
                cls._responses[f] = output
                return output
            else:
                return cls._responses.get(f, None)

        cls._has_run[f] = False
        return wrapper

    @classmethod
    @synchronized_method_call(_LOCK_SINGLETON_CALLABLE)
    def run_once_async(
        cls, f: Callable[PARAM_SPEC_TYPE, Awaitable[ANY_GENERIC_TYPE]]  # type: ignore
    ) -> Callable[PARAM_SPEC_TYPE, Awaitable[ANY_GENERIC_TYPE]]:  # type: ignore
        @functools.wraps(f)
        def wrapper(*args: PARAM_SPEC_TYPE.args, **kwargs: PARAM_SPEC_TYPE.kwargs) -> Awaitable[ANY_GENERIC_TYPE]:
            if not cls._has_run.get(f, False):
                cls._has_run[f.__name__] = True
                return f(*args, **kwargs)
            else:
                return asyncio.sleep(0)

        cls._has_run[f] = False
        return wrapper


class SingletonCachedByKey(type):
    _instances: Any = {}

    @classmethod
    def _get_key(cls, mro, **kwargs: Any) -> tuple[str, ...] | None:
        singleton_key = f'{kwargs.get("id")}'
        for base in mro:
            if base.__module__.startswith("pylav.storage.models"):
                key_name = base.__name__
                if key_name in ("PlayerState", "NodeMock", "Equalizer"):
                    return
                if key_name in ("PlayerConfig", "Config"):
                    singleton_key += f".{kwargs.get('bot')}"
                return singleton_key, key_name

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        # sourcery skip: instance-method-first-arg-name
        key = cls._get_key(cls.mro(), **kwargs)
        if key not in cls._instances:
            rps = cls._locked_call(*args, **kwargs)
            if key is None:
                return rps
        return cls._instances[key]

    @synchronized_method_call(_LOCK_SINGLETON_CACHE_CALLABLE)
    def _locked_call(cls, *args: Any, **kwargs: Any) -> None:
        key = cls._get_key(cls.mro(), **kwargs)
        if key not in cls._instances:
            singleton = super().__call__(*args, **kwargs)
            if key is not None:
                cls._instances[key] = singleton
            else:
                return singleton
