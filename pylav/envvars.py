from __future__ import annotations

import os

# TODO: Remove this PYLAV__POSTGRES_POST
POSTGRE_PORT = os.getenv("PYLAV__POSTGRES_PORT", os.getenv("PYLAV__POSTGRES_POST", "5432"))
POSTGRE_PASSWORD = os.getenv("PYLAV__POSTGRES_PASSWORD", "")
POSTGRE_USER = os.getenv("PYLAV__POSTGRES_USER", "postgres")
POSTGRE_DATABASE = os.getenv("PYLAV__POSTGRES_DB", "postgres")
POSTGRE_HOST = os.getenv("PYLAV__POSTGRES_HOST", "localhost")


try:
    from aioredis import Redis  # noqa

    # This is used specifically for the response cache for  the cached AIOHTTPClient
    REDIS_FULLADDRESS_RESPONSE_CACHE = os.getenv("PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE")
    # redis://[[username]:[password]]@localhost:6379/0
    # unix://[[username]:[password]]@/path/to/socket.sock?db=0
except ImportError:
    REDIS_FULLADDRESS_RESPONSE_CACHE = None
