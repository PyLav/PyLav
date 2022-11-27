import itertools
import warnings

import redis.asyncio as redis
from redis.exceptions import ResponseError as IncrbyException

from pylav.vendored.aiocache.base import BaseCache
from pylav.vendored.aiocache.serializers import JsonSerializer

_NOT_SET = object()


class RedisBackend:

    RELEASE_SCRIPT = (
        "if redis.call('get',KEYS[1]) == ARGV[1] then" " return redis.call('del',KEYS[1])" " else" " return 0" " end"
    )

    CAS_SCRIPT = (
        "if redis.call('get',KEYS[1]) == ARGV[2] then"
        "  if #ARGV == 4 then"
        "   return redis.call('set', KEYS[1], ARGV[1], ARGV[3], ARGV[4])"
        "  else"
        "   return redis.call('set', KEYS[1], ARGV[1])"
        "  end"
        " else"
        " return 0"
        " end"
    )

    def __init__(
        self,
        endpoint="127.0.0.1",
        port=6379,
        db=0,
        password=None,
        pool_min_size=_NOT_SET,
        pool_max_size=None,
        loop=None,
        create_connection_timeout=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if loop is not None:
            warnings.warn(
                "Parameter 'loop' has been obsolete on aiocache >= 0.12.0",
                DeprecationWarning,
            )
        if pool_min_size is not _NOT_SET:
            warnings.warn(
                "Parameter 'pool_min_size' has been obsolete since aiocache >= 0.12.0",
                DeprecationWarning,
            )

        self.endpoint = endpoint
        self.port = int(port)
        self.db = int(db)
        self.password = password
        # NOTE: In redis and aioredis 2.x, ConnectionPool raises ConnectionError
        #  but doesn't wait for connection reuse when number of conns
        #  exceeds the limit. While in aioredis 1.x, it waits asynchronously
        #  via asyncio.Condition. So max pool size defaults to None in redis.
        if pool_max_size is None:
            self.pool_max_size = None
        else:
            self.pool_max_size = int(pool_max_size)
        self.create_connection_timeout = float(create_connection_timeout) if create_connection_timeout else None

        redis_kwargs = {
            "host": self.endpoint,
            "port": self.port,
            "db": self.db,
            "password": self.password,
            # NOTE: decoding can't be controlled on API level after switching to
            #  redis, we need to disable decoding on global/connection level.
            #  Cause some of the values are save as bytes directly, like pickle
            #  serialized values, which may raise exc when decoded with 'utf-8'.
            "decode_responses": False,
            # parameter names are different
            "socket_connect_timeout": self.create_connection_timeout,
            "max_connections": self.pool_max_size,
        }
        self.client = redis.Redis(**redis_kwargs)

    async def _get(self, key, encoding="utf-8", _conn=None):
        value = await self.client.get(key)
        if encoding is None or value is None:
            return value
        return value.decode(encoding)

    async def _gets(self, key, encoding="utf-8", _conn=None):
        return await self._get(key, encoding=encoding, _conn=_conn)

    async def _multi_get(self, keys, encoding="utf-8", _conn=None):
        values = []
        for value in await self.client.mget(*keys):
            if encoding is None or value is None:
                values.append(value)
            else:
                values.append(value.decode(encoding))
        return values

    async def _set(self, key, value, ttl=None, _cas_token=None, _conn=None):
        if _cas_token is not None:
            return await self._cas(key, value, _cas_token, ttl=ttl, _conn=_conn)
        if ttl is None:
            return await self.client.set(key, value)
        if isinstance(ttl, float):
            ttl = int(ttl * 1000)
            return await self.client.psetex(key, ttl, value)
        return await self.client.setex(key, ttl, value)

    async def _cas(self, key, value, token, ttl=None, _conn=None):
        args = [value, token]
        if ttl is not None:
            if isinstance(ttl, float):
                args += ["PX", int(ttl * 1000)]
            else:
                args += ["EX", ttl]
        args = [key] + args
        res = await self._raw("eval", self.CAS_SCRIPT, 1, *args, _conn=_conn)
        return res

    async def _multi_set(self, pairs, ttl=None, _conn=None):
        ttl = ttl or 0

        flattened = list(itertools.chain.from_iterable((key, value) for key, value in pairs))

        if ttl:
            await self.__multi_set_ttl(flattened, ttl)
        else:
            await self.client.execute_command("MSET", *flattened)

        return True

    async def __multi_set_ttl(self, flattened, ttl):
        async with self.client.pipeline(transaction=True) as p:
            p.execute_command("MSET", *flattened)
            if isinstance(ttl, float):
                ttl = int(ttl * 1000)
                for key in flattened[::2]:
                    p.pexpire(key, time=ttl)
            else:
                for key in flattened[::2]:
                    p.expire(key, time=ttl)
            await p.execute()

    async def _add(self, key, value, ttl=None, _conn=None):
        kwargs = {"nx": True}
        if isinstance(ttl, float):
            kwargs.update({"px": int(ttl * 1000)})
        else:
            kwargs.update({"ex": ttl})
        was_set = await self.client.set(key, value, **kwargs)
        if not was_set:
            raise ValueError(f"Key {key} already exists, use .set to update the value")
        return was_set

    async def _exists(self, key, _conn=None):
        number = await self.client.exists(key)
        return bool(number)

    async def _increment(self, key, delta, _conn=None):
        try:
            return await self.client.incrby(key, delta)
        except IncrbyException:
            raise TypeError("Value is not an integer") from None

    async def _expire(self, key, ttl, _conn=None):
        if ttl == 0:
            return await self.client.persist(key)
        return await self.client.expire(key, ttl)

    async def _delete(self, key, _conn=None):
        return await self.client.delete(key)

    async def _clear(self, namespace=None, _conn=None):
        if namespace:
            keys = await self.client.keys(f"{namespace}:*")
            if keys:
                await self.client.delete(*keys)
        else:
            await self.client.flushdb()
        return True

    async def _raw(self, command, *args, encoding="utf-8", _conn=None, **kwargs):
        value = await getattr(self.client, command)(*args, **kwargs)
        if encoding is not None:
            if command == "get" and value is not None:
                value = value.decode(encoding)
            elif command in ["keys", "mget"]:
                value = [_.decode(encoding) if _ is not None else _ for _ in value]
        return value

    async def _redlock_release(self, key, value):
        return await self._raw("eval", self.RELEASE_SCRIPT, 1, key, value)

    async def _close(self, *args, _conn=None, **kwargs):
        await self.client.close()


class RedisCache(RedisBackend, BaseCache):
    """
    Redis cache implementation with the following components as defaults:
        - serializer: :class:`aiocache.serializers.JsonSerializer`
        - plugins: []

    Config options are:

    :param serializer: obj derived from :class:`aiocache.serializers.BaseSerializer`.
    :param plugins: list of :class:`aiocache.plugins.BasePlugin` derived classes.
    :param namespace: string to use as default prefix for the key used in all operations of
        the backend. Default is None.
    :param timeout: int or float in seconds specifying maximum timeout for the operations to last.
        By default its 5.
    :param endpoint: str with the endpoint to connect to. Default is "127.0.0.1".
    :param port: int with the port to connect to. Default is 6379.
    :param db: int indicating database to use. Default is 0.
    :param password: str indicating password to use. Default is None.
    :param pool_max_size: int maximum pool size for the redis connections pool. Default is None.
    :param create_connection_timeout: int timeout for the creation of connection. Default is None
    """

    NAME = "redis"

    def __init__(self, serializer=None, **kwargs):
        super().__init__(**kwargs)
        self.serializer = serializer or JsonSerializer()

    @classmethod
    def parse_uri_path(cls, path):
        """
        Given a uri path, return the Redis specific configuration
        options in that path string according to iana definition
        http://www.iana.org/assignments/uri-schemes/prov/redis

        :param path: string containing the path. Example: "/0"
        :return: mapping containing the options. Example: {"db": "0"}
        """
        options = {}
        db, *_ = path[1:].split("/")
        if db:
            options["db"] = db
        return options

    def _build_key(self, key, namespace=None):
        if namespace is not None:
            return "{}{}{}".format(namespace, ":" if namespace else "", key)
        if self.namespace is not None:
            return "{}{}{}".format(self.namespace, ":" if self.namespace else "", key)
        return key

    def __repr__(self):  # pragma: no cover
        return f"RedisCache ({self.endpoint}:{self.port})"