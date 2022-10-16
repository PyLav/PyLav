import os

from piccolo.engine import PostgresEngine, SQLiteEngine

from pylav._logging import getLogger
from pylav.envvars import POSTGRES_DATABASE, POSTGRES_HOST, POSTGRES_PASSWORD, POSTGRES_PORT, POSTGRES_USER
from pylav.migrations import run_low_level_migrations

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
else:
    LOGGER.info("Connecting to Postgres server using %r", config)
    DB = PostgresEngine(config=config)

run_low_level_migrations(DB)
