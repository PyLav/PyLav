from __future__ import annotations

from piccolo.columns import M2M, BigInt, LazyTableReference, Text
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table

from pylav.storage.database.tables.misc import DATABASE_ENGINE


class PlaylistRow(Table, db=DATABASE_ENGINE, tablename="playlist"):
    id = BigInt(primary_key=True)
    scope = BigInt(null=True, default=None, index=True)
    author = BigInt(null=True, default=None, index=True)
    name = Text(null=True, default=None, index=True, index_method=IndexMethod.gin)
    url = Text(null=True, default=None, index=True)
    tracks = M2M(LazyTableReference("TrackToPlaylists", module_path="pylav.storage.database.tables.m2m"))
