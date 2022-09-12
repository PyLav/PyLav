from __future__ import annotations

import asyncio
import contextlib
import datetime
from typing import TYPE_CHECKING

from discord.utils import utcnow

from pylav._logging import getLogger
from pylav.sql import tables
from pylav.sql.models import QueryModel
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

    async def exists(self, query: Query) -> bool:
        response = await tables.QueryRow.raw(
            "SELECT EXISTS(SELECT 1 FROM query WHERE {}) AS exists".format(
                (
                    (tables.QueryRow.identifier == query.query_identifier)
                    & (tables.QueryRow.last_updated > utcnow() - datetime.timedelta(days=30))
                ).querystring
            )
        )
        return response[0]["exists"] if response else False

    def get(self, identifier: str) -> QueryModel:
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
        query = self.get(query.query_identifier)
        await query.bulk_update(name=name, tracks=[t["track"] async for t in AsyncIter(tracks)])
        return True

    @staticmethod
    async def delete_old() -> None:
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            LOGGER.trace("Deleting old queries")
            await tables.QueryRow.raw(
                "DELETE FROM query WHERE {}".format(
                    (tables.QueryRow.last_updated <= (utcnow() - datetime.timedelta(days=30))).querystring,
                )
            )
            LOGGER.trace("Deleted old queries")

    @staticmethod
    async def wipe() -> None:
        LOGGER.trace("Wiping query cache")
        await tables.QueryRow.raw(
            "TRUNCATE TABLE query",
        )
        LOGGER.trace("Wiped query cache")

    @staticmethod
    async def delete_older_than(days: int) -> None:
        await tables.QueryRow.raw(
            "DELETE FROM query WHERE {}".format(
                (tables.QueryRow.last_updated <= (utcnow() - datetime.timedelta(days=days))).querystring,
            )
        )

    @staticmethod
    async def delete_query(query: Query) -> None:
        await tables.QueryRow.raw("DELETE FROM query WHERE identifier = {}", query.query_identifier)

    @staticmethod
    async def size() -> int:
        response = await tables.QueryRow.raw("SELECT COUNT(identifier) FROM query")
        return response[0]["count"] if response else 0
