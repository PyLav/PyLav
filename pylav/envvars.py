from __future__ import annotations

import os

POSTGRE_PORT = os.getenv("PYLAV__POSTGRES_PORT", "5432")
POSTGRE_PASSWORD = os.getenv("PYLAV__POSTGRES_PASSWORD", "")
POSTGRE_USER = os.getenv("PYLAV__POSTGRES_USER", "postgres")
POSTGRE_DATABASE = os.getenv("PYLAV__POSTGRES_DB", "postgres")
POSTGRE_HOST = os.getenv("PYLAV__POSTGRES_HOST", "localhost")

REDIS_FULLADDRESS_RESPONSE_CACHE = os.getenv("PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE")
