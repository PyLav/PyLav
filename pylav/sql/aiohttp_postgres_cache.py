from collections.abc import AsyncIterable

from aiohttp_client_cache import BaseCache, CacheBackend, ResponseOrKey
from aiohttp_client_cache.docs import extend_init_signature

from pylav.sql import tables


def postgres_template():
    pass


@extend_init_signature(CacheBackend, postgres_template)
class PostgresCacheBackend(CacheBackend):
    """Wrapper for higher-level cache operations. In most cases, the only thing you need to specify here is which storage class(es) to use."""

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
        response = await tables.AioHttpCacheRow.select().where(tables.AioHttpCacheRow.key == key).limit(1)
        return bool(response)

    async def clear(self) -> None:
        """Delete all items from the cache"""
        await tables.AioHttpCacheRow.delete(force=True)

    async def delete(self, key: str) -> None:
        """Delete an item from the cache"""
        await tables.AioHttpCacheRow.delete().where(tables.AioHttpCacheRow.key == key)

    async def keys(self) -> AsyncIterable[str]:
        """Get all keys stored in the cache"""
        async with await tables.AioHttpCacheRow.select(tables.AioHttpCacheRow.key).batch(batch_size=10) as batch:
            async for _batch in batch:
                yield _batch["key"]

    async def read(self, key: str) -> ResponseOrKey:
        """Read an item from the cache"""
        response = (
            await tables.AioHttpCacheRow.select(tables.AioHttpCacheRow.value)
            .where(tables.AioHttpCacheRow.key == key)
            .limit(1)
        )
        if not response:
            return None
        return self.deserialize(response["value"])

    async def size(self) -> int:
        """Get the number of items in the cache"""
        return await tables.AioHttpCacheRow.count()

    def values(self) -> AsyncIterable[ResponseOrKey]:
        """Get all values stored in the cache"""
        return self._values()

    async def _values(self) -> AsyncIterable[ResponseOrKey]:
        async with await tables.AioHttpCacheRow.select(tables.AioHttpCacheRow.value).batch(batch_size=10) as batch:
            async for _batch in batch:
                yield self.deserialize(_batch["value"])

    async def write(self, key: str, item: ResponseOrKey):
        """Write an item to the cache"""

        values = {tables.AioHttpCacheRow.value: self.serialize(item)}
        entry = await tables.AioHttpCacheRow.objects().get_or_create(tables.AioHttpCacheRow.key == key, defaults=values)
        if not entry._was_created:
            await tables.AioHttpCacheRow.update(values).where(tables.AioHttpCacheRow.key == key)

    async def bulk_delete(self, keys: set[str]) -> None:
        """Delete multiple items from the cache"""
        await tables.AioHttpCacheRow.delete().where(tables.AioHttpCacheRow.key.is_in(list(keys)))
