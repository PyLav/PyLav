import logging
from typing import Dict, Type

from pylav.vendored.aiocache._version import __version__
from pylav.vendored.aiocache.backends.memory import SimpleMemoryCache
from pylav.vendored.aiocache.base import BaseCache

logger = logging.getLogger(__name__)

AIOCACHE_CACHES: dict[str, type[BaseCache]] = {SimpleMemoryCache.NAME: SimpleMemoryCache}

try:
    import redis
except ImportError:
    logger.info("redis not installed, RedisCache unavailable")
else:
    from pylav.vendored.aiocache.backends.redis import RedisCache

    AIOCACHE_CACHES[RedisCache.NAME] = RedisCache
    del redis

try:
    import aiomcache
except ImportError:
    logger.info("aiomcache not installed, Memcached unavailable")
else:
    from pylav.vendored.aiocache.backends.memcached import MemcachedCache

    AIOCACHE_CACHES[MemcachedCache.NAME] = MemcachedCache
    del aiomcache

from pylav.vendored.aiocache.decorators import cached, cached_stampede, multi_cached  # noqa: E402,I202
from pylav.vendored.aiocache.factory import Cache, caches  # noqa: E402

__all__ = (
    "caches",
    "Cache",
    "cached",
    "cached_stampede",
    "multi_cached",
    *(c.__name__ for c in AIOCACHE_CACHES.values()),
    "__version__",
)
