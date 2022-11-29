import os

from piccolo.engine import PostgresEngine, SQLiteEngine

from pylav._logging import getLogger
from pylav.envvars import POSTGRES_DATABASE, POSTGRES_HOST, POSTGRES_PASSWORD, POSTGRES_PORT, POSTGRES_USER

config = {
    "host": POSTGRES_HOST,
    "port": int(POSTGRES_PORT) if isinstance(POSTGRES_PORT, str) else POSTGRES_PORT,
    "database": POSTGRES_DATABASE,
    "user": POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
}
LOGGER = getLogger("PyLav.Postgres")

if os.getenv("BUILDING_DOCS", False):
    DB = SQLiteEngine()
    IS_POSTGRES = False
else:
    LOGGER.verbose("Connecting to Postgres server using %r", config)
    DB = PostgresEngine(
        config=config,
        extensions=(
            "uuid-ossp",
            "btree_gin",
        ),
    )
    IS_POSTGRES = True
