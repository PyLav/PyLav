from __future__ import annotations

from piccolo.columns import JSONB, BigInt, Text
from piccolo.table import Table

from pylav.sql.tables.init import DB


class PlaylistRow(Table, db=DB, tablename="playlist"):
    id = BigInt(primary_key=True)
    scope = BigInt(null=True, default=None)
    author = BigInt(null=True, default=None)
    name = Text(null=True, default=None)
    url = Text(null=True, default=None)
    tracks = JSONB(null=False, default=[])
