from __future__ import annotations

import asyncio
import contextlib
import datetime
from typing import TYPE_CHECKING

import asyncpg

from pylav.helpers.time import get_now_utc
from pylav.logging import getLogger
from pylav.players.query.obj import Query as QueryObj
from pylav.storage.database.tables.queries import QueryRow
from pylav.storage.database.tables.tracks import TrackRow
from pylav.storage.models.query import Query
from pylav.type_hints.dict_typing import JSON_DICT_TYPE
from pylav.utils.vendor.redbot import AsyncIter

if TYPE_CHECKING:
    from pylav.core.client import Client
LOGGER = getLogger("PyLav.Database.Controller.Query")


class QueryController:
    __slots__ = ("_client",)

    def __init__(self, client: Client) -> None:
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    async def exists(query: QueryObj) -> bool:
        return await QueryRow.exists().where(
            (QueryRow.identifier == query.query_identifier)
            & (QueryRow.last_updated > get_now_utc() - datetime.timedelta(days=30))
        )

    @staticmethod
    def get(identifier: str) -> Query:
        """Get a query object"""
        return Query(id=identifier)

    async def fetch_query(self, query: QueryObj) -> Query | None:
        if query.is_local or query.is_custom_playlist or query.is_http:
            # Do not cache local queries and single track urls or http source entries
            return None

        if await self.exists(query):
            cached = self.get(query.query_identifier)
            if await cached.size() > 0:
                return cached

    @staticmethod
    async def add_query(query: QueryObj, result: JSON_DICT_TYPE) -> bool:
        if query.is_local or query.is_custom_playlist or query.is_http:
            # Do not cache local queries and single track urls or http source entries
            return False
        if result.get("loadType") in ["NO_MATCHES", "LOAD_FAILED", None]:
            return False
        tracks = result.get("tracks", [])
        if not tracks:
            return False
        playlist_info = result.get("playlistInfo", {})
        name = playlist_info.get("name", None) if playlist_info else None
        defaults = {QueryRow.name: name}
        query_row = await QueryRow.objects().get_or_create(QueryRow.identifier == query.query_identifier, defaults)

        # noinspection PyProtectedMember
        if not query_row._was_created:
            await QueryRow.update(defaults).where(QueryRow.identifier == query.query_identifier)
        new_tracks = []
        # TODO: Optimize this, after https://github.com/piccolo-orm/piccolo/discussions/683 is answered or fixed
        async for track in AsyncIter(tracks):
            with contextlib.suppress(Exception):
                new_info = {
                    key: track["info"][key]
                    for key in track["info"].keys()
                    if key in {"identifier", "sourceName", "title", "uri", "isrc"}
                }
                new_tracks.append(await TrackRow.get_or_create(track["encoded"], new_info))
        if new_tracks:
            await query_row.add_m2m(*new_tracks, m2m=QueryRow.tracks)
            return True
        await QueryRow.delete().where(QueryRow.identifier == query.query_identifier)
        return False

    @staticmethod
    async def delete_old() -> None:
        with contextlib.suppress(asyncio.exceptions.CancelledError, asyncpg.exceptions.CannotConnectNowError):
            LOGGER.trace("Deleting old queries")
            await QueryRow.delete().where(QueryRow.last_updated <= (get_now_utc() - datetime.timedelta(days=30)))
            LOGGER.trace("Deleted old queries")

    @staticmethod
    async def wipe() -> None:
        LOGGER.trace("Wiping query cache")
        await QueryRow.raw(
            "TRUNCATE TABLE query",
        )
        LOGGER.trace("Wiped query cache")

    @staticmethod
    async def delete_older_than(days: int) -> None:
        await QueryRow.delete().where(QueryRow.last_updated <= (get_now_utc() - datetime.timedelta(days=days)))

    @staticmethod
    async def delete_query(query: QueryObj) -> None:
        await QueryRow.delete().where(QueryRow.identifier == query.query_identifier)

    @staticmethod
    async def size() -> int:
        return await QueryRow.count()
