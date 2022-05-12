from __future__ import annotations

import getpass
import os

if getpass.getuser() == "draper":  # FIXME: This is a hack im lazy and should be removed before release
    POSTGRE_DATABASE = "py_lav"
    POSTGRE_USER = "draper"
    POSTGRE_PASSWORD = "testing"  # noqa
    POSTGRE_PORT = "5433"
else:
    # TODO: Remove this PYLAV__POSTGRES_POST
    POSTGRE_PORT = os.getenv("PYLAV__POSTGRES_PORT", os.getenv("PYLAV__POSTGRES_POST", "5432"))
    POSTGRE_PASSWORD = os.getenv("PYLAV__POSTGRES_PASSWORD", "")
    POSTGRE_USER = os.getenv("PYLAV__POSTGRES_USER", "postgres")
    POSTGRE_DATABASE = os.getenv("PYLAV__POSTGRES_DB", "postgres")
POSTGRE_HOST = os.getenv("PYLAV__POSTGRES_HOST", "localhost")


try:
    pass

    REDIS_HOST = os.getenv("PYLAV__REDIS_HOST")
    REDIS_PORT = os.getenv("PYLAV__REDIS_PORT")
    REDIS_DB = os.getenv("PYLAV__REDIS_DB", "0")
    REDIS_PASSWORD = os.getenv("PYLAV__REDIS_PASSWORD", "")
except ImportError:  # pragma: nocover
    REDIS_HOST = None
    REDIS_PORT = None
    REDIS_DB = None
    REDIS_PASSWORD = None

try:
    pass

    # This is used specifically for the response cache for  the cached AIOHTTPClient
    REDIS_FULLADDRESS_RESPONSE_CACHE = os.getenv("PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE")
    # redis://[[username]:[password]]@localhost:6379/0
    # unix://[[username]:[password]]@/path/to/socket.sock?db=0
except ImportError:  # pragma: nocover

    REDIS_FULLADDRESS_RESPONSE_CACHE = None
