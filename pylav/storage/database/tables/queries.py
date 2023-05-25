from __future__ import annotations

from piccolo.columns import JSONB, M2M, LazyTableReference, Text, Timestamptz
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table

from pylav.helpers.time import get_now_utc
from pylav.storage.database.tables.misc import DATABASE_ENGINE


class QueryRow(Table, db=DATABASE_ENGINE, tablename="query"):
    identifier = Text(null=False, index=True, primary_key=True)
    name = Text(null=True, default=None)
    last_updated = Timestamptz(null=False, index=True, default=TimestamptzNow(), auto_update=get_now_utc)
    pluginInfo = JSONB(null=True, default=None)
    tracks = M2M(LazyTableReference("TrackToQueries", module_path="pylav.storage.database.tables.m2m"))
    info = JSONB(null=True, default=None)
