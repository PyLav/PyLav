from __future__ import annotations

from piccolo.columns import ForeignKey
from piccolo.table import Table

from pylav.sql.tables.init import DB
from pylav.sql.tables.playlists import PlaylistRow
from pylav.sql.tables.queries import QueryRow
from pylav.sql.tables.tracks import TrackRow


class TrackToQueries(Table, db=DB):
    queries = ForeignKey(QueryRow)
    tracks = ForeignKey(TrackRow)


class TrackToPlaylists(Table, db=DB):
    playlists = ForeignKey(PlaylistRow)
    tracks = ForeignKey(TrackRow)
