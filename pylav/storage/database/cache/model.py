from __future__ import annotations

import inspect
from collections.abc import Callable, Iterator
from typing import Any

from pylav.storage.database.cache.functions import invalidate_cache_multi, update_cache_multi


class CachedModel:
    @staticmethod
    def _predicate(member: Callable) -> bool:
        """Check if the method is a cached method"""
        if getattr(member, "__name__", "_").startswith("_"):
            return False
        return bool(hasattr(member, "cache")) if inspect.ismethod(member) else False

    def get_all_methods(self) -> Iterator[Callable]:
        """Get all methods of the class"""

        return [_callable for member, _callable in inspect.getmembers(self, predicate=self._predicate)]

    async def invalidate_cache(self, *methods: Callable) -> None:
        """Invalidate the cache for the given methods if not specify all"""
        if methods:
            await invalidate_cache_multi(methods, self)
        else:
            await invalidate_cache_multi(self.get_all_methods(), self)

    async def update_cache(self, *pairs: tuple[Callable, Any]) -> None:
        """Update the cache for the specified method"""
        await update_cache_multi(pairs, self)
