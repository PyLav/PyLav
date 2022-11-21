from __future__ import annotations

from discord.utils import utcnow
from piccolo.columns import M2M, LazyTableReference, Text, Timestamptz
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table

from pylav.sql.tables.init import DB


class QueryRow(Table, db=DB, tablename="query"):
    identifier = Text(null=False, index=True, primary_key=True)
    name = Text(null=True, default=None)
    last_updated = Timestamptz(null=False, index=True, default=TimestamptzNow(), auto_update=utcnow)
    tracks = M2M(LazyTableReference("TrackToQueries", module_path="pylav.sql.tables.m2m"))
