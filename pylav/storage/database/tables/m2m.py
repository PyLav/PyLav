from __future__ import annotations

from piccolo.columns import ForeignKey
from piccolo.table import Table

from pylav.storage.database.tables.misc import DATABASE_ENGINE
from pylav.storage.database.tables.playlists import PlaylistRow
from pylav.storage.database.tables.queries import QueryRow
from pylav.storage.database.tables.tracks import TrackRow


class TrackToQueries(Table, db=DATABASE_ENGINE):
    queries = ForeignKey(QueryRow)
    tracks = ForeignKey(TrackRow)


class TrackToPlaylists(Table, db=DATABASE_ENGINE):
    playlists = ForeignKey(PlaylistRow)
    tracks = ForeignKey(TrackRow)
