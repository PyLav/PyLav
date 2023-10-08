from __future__ import annotations

from collections.abc import AsyncIterable
from typing import Any

from aiohttp_client_cache import BaseCache, CacheBackend, ResponseOrKey

from pylav.storage.database.tables.aiohttp_cache import AioHttpCacheRow


def postgres_template() -> None:
    pass


class PostgresCacheBackend(CacheBackend):
    """Wrapper for higher-level cache operations.
    In most cases, the only thing you need to specify here is which storage class(es) to use"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.redirects = PostgresStorage(**kwargs)
        self.responses = PostgresStorage(**kwargs)


class PostgresStorage(BaseCache):
    """interface for lower-level backend storage operations"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def contains(self, key: str) -> bool:
        """Check if a key is stored in the cache"""
        return await AioHttpCacheRow.exists().where(AioHttpCacheRow.key == key)

    async def clear(self) -> None:
        """Delete all items from the cache"""
        await AioHttpCacheRow.raw("TRUNCATE TABLE aiohttp_client_cache")

    async def delete(self, key: str) -> None:
        """Delete an item from the cache"""
        await AioHttpCacheRow.delete().where(AioHttpCacheRow.key == key)

    async def keys(self) -> AsyncIterable[str]:
        """Get all keys stored in the cache"""
        for entry in await AioHttpCacheRow.select(AioHttpCacheRow.key).output(load_json=True, nested=True):
            yield entry["key"]

    async def read(self, key: str) -> ResponseOrKey:
        """Read an item from the cache"""
        response = (
            await AioHttpCacheRow.select(AioHttpCacheRow.value)
            .where(AioHttpCacheRow.key == key)
            .first()
            .output(load_json=True, nested=True)
        )
        return self.deserialize(response["value"]) if response else None

    async def size(self) -> int:
        """Get the number of items in the cache"""
        return await AioHttpCacheRow.count()

    def values(self) -> AsyncIterable[ResponseOrKey]:
        """Get all values stored in the cache"""
        return self._values()

    async def _values(self) -> AsyncIterable[ResponseOrKey]:
        for entry in await AioHttpCacheRow.select(AioHttpCacheRow.value).output(load_json=True, nested=True):
            yield self.deserialize(entry["value"])

    async def write(self, key: str, item: ResponseOrKey) -> None:
        """Write an item to the cache"""
        await AioHttpCacheRow.insert(AioHttpCacheRow(key=key, value=self.serialize(item))).on_conflict(
            action="DO NOTHING", target=AioHttpCacheRow.key
        )

    async def bulk_delete(self, keys: set[str]) -> None:
        """Delete multiple items from the cache"""
        await AioHttpCacheRow.delete().where(AioHttpCacheRow.key.is_in(list(keys)))
