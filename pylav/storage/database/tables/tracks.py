from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from asyncpg import UniqueViolationError  # type: ignore
from piccolo.columns import JSONB, M2M, LazyTableReference, Text
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table

from pylav.logging import getLogger
from pylav.storage.database.tables.misc import DATABASE_ENGINE

if TYPE_CHECKING:
    from pylav.nodes.api.responses.track import Track

LOGGER = getLogger("PyLav.Database.Track")
_LOCK = asyncio.Lock()


class TrackRow(Table, db=DATABASE_ENGINE, tablename="track"):
    identifier = Text(null=True, default=None, index=True)
    sourceName = Text(null=True, default=None, index=True)
    title = Text(null=True, default=None, index=True, index_method=IndexMethod.gin)
    uri = Text(null=True, default=None, index=True)
    isrc = Text(null=True, default=None, index=True)
    encoded = Text(null=False, index=True, primary_key=True)
    artworkUrl = Text(null=True, default=None)
    info = JSONB(null=True, default=None)
    pluginInfo = JSONB(null=True, default=None)
    queries = M2M(LazyTableReference("TrackToQueries", module_path="pylav.storage.database.tables.m2m"))
    playlists = M2M(LazyTableReference("TrackToPlaylists", module_path="pylav.storage.database.tables.m2m"))

    @classmethod
    async def get_or_create(
        cls,
        track: Track,
    ) -> TrackRow:
        async with _LOCK:
            try:
                kwargs = {
                    TrackRow.identifier: track.info.identifier,
                    TrackRow.sourceName: track.info.sourceName,
                    TrackRow.title: track.info.title,
                    TrackRow.uri: track.info.uri,
                    TrackRow.isrc: track.info.isrc,
                    TrackRow.encoded: track.encoded,
                    TrackRow.artworkUrl: track.info.artworkUrl,
                    TrackRow.info: track.info.to_dict(),
                    TrackRow.pluginInfo: track.pluginInfo.to_dict() if track.pluginInfo else None,
                }

                track = await cls.objects().get_or_create(cls.encoded == track.encoded, kwargs)
                if (not track._was_created) and (
                    (track.info is None and kwargs.get(cls.info._meta.db_column_name))
                    or (track.pluginInfo is None and kwargs.get(cls.pluginInfo._meta.db_column_name))
                ):
                    await cls.update({k._meta.db_column_name: v for k, v in kwargs.items()}).where(
                        cls.encoded == track.encoded
                    )
                return track
            except UniqueViolationError:
                obj = cls(encoded=track.encoded, **{k._meta.db_column_name: v for k, v in kwargs.items()})
                obj._exists_in_db = True
                return obj
            except Exception as e:
                LOGGER.trace("Error while creating track: %s", e, exc_info=True)
                raise e
