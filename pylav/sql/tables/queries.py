from __future__ import annotations

from piccolo.columns import JSONB, Text, Timestamptz
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table

from pylav.sql.tables.init import DB


class QueryRow(Table, db=DB, tablename="query"):
    identifier = Text(null=False, index=True, primary_key=True)
    name = Text(null=True, default=None)
    tracks = JSONB(null=False, default=[])
    last_updated = Timestamptz(null=False, index=True, default=TimestamptzNow())
