from __future__ import annotations

import os

POSTGRE_PORT = os.getenv("PYLAV__POSTGRES_PORT", os.getenv("PGPORT"))
POSTGRE_PASSWORD = os.getenv("PYLAV__POSTGRES_PASSWORD", os.getenv("PGPASSWORD"))
POSTGRE_USER = os.getenv("PYLAV__POSTGRES_USER", os.getenv("PGUSER"))
POSTGRE_DATABASE = os.getenv("PYLAV__POSTGRES_DB", os.getenv("PGDATABASE"))
POSTGRE_HOST = os.getenv("PYLAV__POSTGRES_HOST", os.getenv("PGHOST"))

REDIS_FULLADDRESS_RESPONSE_CACHE = os.getenv("PYLAV__REDIS_FULLADDRESS_RESPONSE_CACHE")
