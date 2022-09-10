from __future__ import annotations

from piccolo.engine import PostgresEngine, SQLiteEngine


def run_low_level_migrations(db: PostgresEngine | SQLiteEngine) -> None:
    """
    Runs migrations.
    """
    # from piccolo.utils.sync import run_sync
    # con = run_sync(db.get_connection())

    # run_sync(db.get_connection("playlist", if_not_exists=True))
