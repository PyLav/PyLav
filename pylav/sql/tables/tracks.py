from __future__ import annotations

from asyncpg import UniqueViolationError
from piccolo.columns import M2M, Boolean, Integer, LazyTableReference, Text
from piccolo.table import Table

from pylav.sql.tables.init import DB
from pylav.utils import _LOCK, LOGGER, _synchronized


class TrackRow(Table, db=DB, tablename="track"):
    identifier = Text(null=False, index=True)
    sourceName = Text(null=True, default=None)
    title = Text(null=False, default="", index=True)
    author = Text(null=False, index=True)
    uri = Text(null=True, default=None)
    length = Integer(null=False, default=0, index=True)
    position = Integer(null=True, default=0)
    isSeekable = Boolean(null=False)
    isStream = Boolean(null=False, default=False)
    encoded = Text(null=False, index=True, primary_key=True)
    queries = M2M(LazyTableReference("TrackToQueries", module_path="pylav.sql.tables.m2m"))
    playlists = M2M(LazyTableReference("TrackToPlaylists", module_path="pylav.sql.tables.m2m"))

    @classmethod
    @_synchronized(_LOCK)
    async def get_or_create(cls, encoded: str, kwargs: dict):
        try:
            return await cls.objects().get_or_create(cls.encoded == encoded, kwargs)
        except UniqueViolationError:
            obj = cls(encoded=encoded, **kwargs)
            obj._exists_in_db = True
            return obj
        except Exception as e:
            LOGGER.trace(f"Error while creating track: %s", e, exc_info=True)
            raise e