from collections.abc import AsyncIterable

from aiohttp_client_cache import BaseCache, CacheBackend, ResponseOrKey
from aiohttp_client_cache.docs import extend_init_signature

from pylav.sql import tables


def postgres_template():
    pass


@extend_init_signature(CacheBackend, postgres_template)
class PostgresCacheBackend(CacheBackend):
    """Wrapper for higher-level cache operations.
    In most cases, the only thing you need to specify here is which storage class(es) to use"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.redirects = PostgresStorage(**kwargs)
        self.responses = PostgresStorage(**kwargs)


class PostgresStorage(BaseCache):
    """interface for lower-level backend storage operations"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def contains(self, key: str) -> bool:
        """Check if a key is stored in the cache"""
        response = await tables.AioHttpCacheRow.raw(
            "SELECT EXISTS(SELECT 1 FROM aiohttp_client_cache WHERE key ={} LIMIT 1) AS exists", key
        )
        return response[0]["exists"] if response else False

    async def clear(self) -> None:
        """Delete all items from the cache"""
        await tables.AioHttpCacheRow.raw("TRUNCATE TABLE aiohttp_client_cache")

    async def delete(self, key: str) -> None:
        """Delete an item from the cache"""
        await tables.AioHttpCacheRow.raw("DELETE FROM aiohttp_client_cache WHERE key = {}", key)

    async def keys(self) -> AsyncIterable[str]:
        """Get all keys stored in the cache"""
        async with await tables.AioHttpCacheRow.select(tables.AioHttpCacheRow.key).batch(batch_size=10) as batch:
            async for _batch in batch:
                yield _batch["key"]

    async def read(self, key: str) -> ResponseOrKey:
        """Read an item from the cache"""
        response = await tables.AioHttpCacheRow.raw(
            "SELECT value FROM aiohttp_client_cache WHERE key = {} LIMIT 1", key
        )
        return self.deserialize(response["value"]) if response else None

    async def size(self) -> int:
        """Get the number of items in the cache"""
        response = await tables.AioHttpCacheRow.raw("SELECT COUNT(*) FROM aiohttp_client_cache")
        return response[0]["count"] if response else 0

    def values(self) -> AsyncIterable[ResponseOrKey]:
        """Get all values stored in the cache"""
        return self._values()

    async def _values(self) -> AsyncIterable[ResponseOrKey]:
        async with await tables.AioHttpCacheRow.select(tables.AioHttpCacheRow.value).batch(batch_size=10) as batch:
            async for _batch in batch:
                yield self.deserialize(_batch["value"])

    async def write(self, key: str, item: ResponseOrKey):
        """Write an item to the cache"""

        await tables.AioHttpCacheRow.raw(
            """
            INSERT INTO aiohttp_client_cache (key, value)
            VALUES ({}, {})
            ON CONFLICT (key) DO NOTHING
            """,
            key,
            self.serialize(item),
        )

    async def bulk_delete(self, keys: set[str]) -> None:
        """Delete multiple items from the cache"""
        await tables.AioHttpCacheRow.raw(
            f"""
            DELETE FROM aiohttp_client_cache
            WHERE {tables.AioHttpCacheRow.key.is_in(list(keys)).querystring}
            """,
        )
