from __future__ import annotations

import asyncio
import contextlib
import datetime
from typing import TYPE_CHECKING

from discord.utils import utcnow

import pylav.sql.tables.queries
import pylav.sql.tables.tracks
from pylav._logging import getLogger
from pylav.sql.models import QueryModel
from pylav.sql.tables import DB
from pylav.utils import AsyncIter

if TYPE_CHECKING:
    from pylav.client import Client
    from pylav.query import Query

LOGGER = getLogger("PyLav.QueryCacheManager")


class QueryCacheManager:
    __slots__ = ("_client",)

    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    async def exists(query: Query) -> bool:
        return await pylav.sql.tables.queries.QueryRow.exists().where(
            (pylav.sql.tables.queries.QueryRow.identifier == query.query_identifier)
            & (pylav.sql.tables.queries.QueryRow.last_updated > utcnow() - datetime.timedelta(days=30))
        )

    @staticmethod
    def get(identifier: str) -> QueryModel:
        """Get a query object"""
        return QueryModel(id=identifier)

    async def fetch_query(self, query: Query) -> QueryModel | None:
        if query.is_local or query.is_custom_playlist or query.is_http:
            # Do not cache local queries and single track urls or http source entries
            return None

        if await self.exists(query):
            return self.get(query.query_identifier)

    async def add_query(self, query: Query, result: dict) -> bool:
        if query.is_local or query.is_custom_playlist or query.is_http:
            # Do not cache local queries and single track urls or http source entries
            return False
        if result.get("loadType") in ["NO_MATCHES", "LOAD_FAILED", None]:
            return False
        tracks = result.get("tracks", [])
        if not tracks:
            return False
        name = result.get("playlistInfo", {}).get("name", None)
        defaults = {pylav.sql.tables.queries.QueryRow.name: name}
        query_row = await pylav.sql.tables.queries.QueryRow.objects().get_or_create(
            pylav.sql.tables.queries.QueryRow.identifier == query.query_identifier, defaults
        )
        if not query_row._was_created:
            await pylav.sql.tables.queries.QueryRow.update(defaults).where(
                pylav.sql.tables.queries.QueryRow.identifier == query.query_identifier
            )
        new_tracks = []
        # TODO: Optimize this, after https://github.com/piccolo-orm/piccolo/discussions/683 is answered or fixed
        async with DB.transaction():
            async for track in AsyncIter(tracks):
                with contextlib.suppress(Exception):
                    new_tracks.append(
                        await pylav.sql.tables.tracks.TrackRow.objects().get_or_create(
                            pylav.sql.tables.tracks.TrackRow.encoded == track["encoded"], track["info"]
                        )
                    )
        if new_tracks:
            await query_row.add_m2m(*new_tracks, m2m=pylav.sql.tables.queries.QueryRow.tracks)
            return True
        return False

    @staticmethod
    async def delete_old() -> None:
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            LOGGER.trace("Deleting old queries")
            await pylav.sql.tables.queries.QueryRow.delete().where(
                pylav.sql.tables.queries.QueryRow.last_updated <= (utcnow() - datetime.timedelta(days=30))
            )
            LOGGER.trace("Deleted old queries")

    @staticmethod
    async def wipe() -> None:
        LOGGER.trace("Wiping query cache")
        await pylav.sql.tables.queries.QueryRow.raw(
            "TRUNCATE TABLE query",
        )
        LOGGER.trace("Wiped query cache")

    @staticmethod
    async def delete_older_than(days: int) -> None:
        await pylav.sql.tables.queries.QueryRow.delete().where(
            pylav.sql.tables.queries.QueryRow.last_updated <= (utcnow() - datetime.timedelta(days=days))
        )

    @staticmethod
    async def delete_query(query: Query) -> None:
        await pylav.sql.tables.queries.QueryRow.delete().where(
            pylav.sql.tables.queries.QueryRow.identifier == query.query_identifier
        )

    @staticmethod
    async def size() -> int:
        return await pylav.sql.tables.queries.QueryRow.count()
