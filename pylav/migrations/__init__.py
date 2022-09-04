from __future__ import annotations

from piccolo.engine import PostgresEngine, SQLiteEngine
from piccolo.utils.sync import run_sync


def run_low_level_migrations(db: PostgresEngine | SQLiteEngine) -> None:
    """
    Runs migrations.
    """
    # con = run_sync(db.get_connection())

    # run_sync(db.get_connection("playlist", if_not_exists=True))
