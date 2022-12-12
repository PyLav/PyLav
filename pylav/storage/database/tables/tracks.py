from __future__ import annotations

import threading

from asyncpg import UniqueViolationError  # type: ignore
from piccolo.columns import M2M, LazyTableReference, Text
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table

from pylav.helpers.singleton import synchronized_method_call
from pylav.logging import getLogger
from pylav.storage.database.tables.misc import DATABASE_ENGINE
from pylav.type_hints.dict_typing import JSON_DICT_TYPE

LOGGER = getLogger("PyLav.Database.Track")
_LOCK = threading.Lock()


class TrackRow(Table, db=DATABASE_ENGINE, tablename="track"):
    identifier = Text(null=True, default=None, index=True)
    sourceName = Text(null=True, default=None, index=True)
    title = Text(null=True, default=None, index=True, index_method=IndexMethod.gin)
    uri = Text(null=True, default=None, index=True)
    # noinspection SpellCheckingInspection
    isrc = Text(null=True, default=None, index=True)
    encoded = Text(null=False, index=True, primary_key=True)
    queries = M2M(LazyTableReference("TrackToQueries", module_path="pylav.storage.database.tables.m2m"))
    playlists = M2M(LazyTableReference("TrackToPlaylists", module_path="pylav.storage.database.tables.m2m"))

    @classmethod
    @synchronized_method_call(_LOCK)
    async def get_or_create(cls, encoded: str, kwargs: JSON_DICT_TYPE) -> TrackRow:
        try:
            return await cls.objects().get_or_create(cls.encoded == encoded, kwargs)
        except UniqueViolationError:
            obj = cls(encoded=encoded, **kwargs)
            obj._exists_in_db = True
            return obj
        except Exception as e:
            LOGGER.trace("Error while creating track: %s", e, exc_info=True)
            raise e
