from __future__ import annotations

import threading
from typing import Any

_LOCK = threading.Lock()


class CachedSingletonByKey(type):
    _instances: Any = {}

    @classmethod
    def _get_key(cls, mro, **kwargs):  # noqa
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

    @synchronized_method_call(_LOCK)
    def _locked_call(cls, *args, **kwargs):
        key = cls._get_key(cls.mro(), **kwargs)
        if key not in cls._instances:
            singleton = super().__call__(*args, **kwargs)
            cls._instances[key] = singleton
