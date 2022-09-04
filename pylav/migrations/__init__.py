from __future__ import annotations

from piccolo.engine import PostgresEngine, SQLiteEngine


def run_low_level_migrations(db: PostgresEngine | SQLiteEngine) -> None:
    """
    Runs migrations.
    """
