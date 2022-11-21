from __future__ import annotations

from piccolo.columns import M2M, BigInt, LazyTableReference, Text
from piccolo.table import Table

from pylav.sql.tables.init import DB


class PlaylistRow(Table, db=DB, tablename="playlist"):
    id = BigInt(primary_key=True)
    scope = BigInt(null=True, default=None)
    author = BigInt(null=True, default=None)
    name = Text(null=True, default=None)
    url = Text(null=True, default=None)
    tracks = M2M(LazyTableReference("TrackToPlaylists", module_path="pylav.sql.tables.m2m"))
