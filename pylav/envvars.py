from __future__ import annotations

import os

# TODO: Remove this PYLAV__POSTGRES_POST
POSTGRE_PORT = os.getenv("PYLAV__POSTGRES_PORT", os.getenv("PYLAV__POSTGRES_POST", "5432"))
POSTGRE_PASSWORD = os.getenv("PYLAV__POSTGRES_PASSWORD", "")
POSTGRE_USER = os.getenv("PYLAV__POSTGRES_USER", "postgres")
POSTGRE_DATABASE = os.getenv("PYLAV__POSTGRES_DB", "postgres")
POSTGRE_HOST = os.getenv("PYLAV__POSTGRES_HOST", "localhost")


try:
    from redis import Redis  # noqa

    REDIS_HOST = os.getenv("PYLAV__REDIS_HOST")
    REDIS_PORT = os.getenv("PYLAV__REDIS_PORT")
    REDIS_USERNAME = os.getenv("PYLAV__REDIS_USERNAME")
    REDIS_DB = os.getenv("PYLAV__REDIS_DB", "0")
    REDIS_PASSWORD = os.getenv("PYLAV__REDIS_PASSWORD", "")
    REDIS_UNIX_SOCKET_PATH = os.getenv("PYLAV__REDIS_UNIX_SOCKET_PATH")
except ImportError:
    REDIS_HOST = None
    REDIS_PORT = None
    REDIS_USERNAME = None
    REDIS_DB = None
    REDIS_PASSWORD = None
    REDIS_UNIX_SOCKET_PATH = None

try:
    from aioredis import Redis  # noqa

    # This is used specifically for the response cache for  the cached AIOHTTPClient
    REDIS_FULLADDRESS_RESPONSE_CACHE = os.getenv("PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE")
    # redis://[[username]:[password]]@localhost:6379/0
    # unix://[[username]:[password]]@/path/to/socket.sock?db=0
except ImportError:
    REDIS_FULLADDRESS_RESPONSE_CACHE = None
