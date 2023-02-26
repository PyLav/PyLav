from __future__ import annotations

import os

from piccolo.engine import PostgresEngine, SQLiteEngine

from pylav.constants.config import POSTGRES_DATABASE, POSTGRES_HOST, POSTGRES_PASSWORD, POSTGRES_PORT, POSTGRES_USER
from pylav.logging import getLogger

_CONFIG = {
    "host": POSTGRES_HOST,
    "port": int(POSTGRES_PORT) if isinstance(POSTGRES_PORT, str) else POSTGRES_PORT,
    "database": POSTGRES_DATABASE,
    "user": POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
}
LOGGER = getLogger("PyLav.Postgres")
DATABASE_ENGINE: PostgresEngine | SQLiteEngine
if os.getenv("PYLAV__SQL", False):
    DATABASE_ENGINE = SQLiteEngine()
    IS_POSTGRES = False
else:
    LOGGER.verbose("Connecting to Postgres server using %r", _CONFIG)
    # noinspection SpellCheckingInspection
    DATABASE_ENGINE = PostgresEngine(
        config=_CONFIG,
        extensions=(
            "uuid-ossp",
            "pg_trgm",
            "btree_gin",
        ),
    )
    IS_POSTGRES = True
