from __future__ import annotations

import asyncio
import datetime
import pathlib
from typing import TYPE_CHECKING

import ujson
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from pylav._config import CONFIG_DIR
from pylav.cache.models import Base, QueryDBEntry, QueryTrackDBEntry, TrackDBEntry
from pylav.utils import AsyncIter

if TYPE_CHECKING:
    from pylav.client import Client


class CacheManager:
    def __init__(self, client: Client, config_folder: pathlib.Path = CONFIG_DIR, sql_connection_string: str = None):
        __database_folder: pathlib.Path = config_folder
        __default_db_name: pathlib.Path = __database_folder / "queries.db"
        if not sql_connection_string or "sqlite+aiosqlite:///" in sql_connection_string:
            sql_connection_string = f"sqlite+aiosqlite:///{__default_db_name}"

        if "sqlite" in sql_connection_string:
            from sqlalchemy.dialects.sqlite import Insert

            self._insert = Insert
        else:
            from sqlalchemy.dialects.postgresql import Insert

            self._insert = Insert
        self._engine = create_async_engine(
            sql_connection_string, json_deserializer=ujson.loads, json_serializer=ujson.dumps
        )
        self._session = sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)
        self._client = client

        event.listen(self._engine.sync_engine, "connect", self.on_db_connect)

    @staticmethod
    def on_db_connect(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA temp_store=2")
        cursor.execute("PRAGMA read_uncommitted=1")
        cursor.execute("PRAGMA optimize")
        cursor.close()

    async def init(self):
        await self.create_tables()

    @property
    def client(self) -> Client:
        return self._client

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session(self) -> AsyncSession:
        return self._session()

    async def close(self):
        self._engine.dispose()

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()

    async def upsert_queries(self, queries: list[dict]):
        async with self.session as session:
            async with session.begin():
                async for query in AsyncIter(queries):
                    query_id = query["id"]
                    query_name = query["name"]
                    tracks = query["tracks"]
                    query_values = [dict(id=query_id, name=query_name)]
                    query_insert_op = await asyncio.to_thread(self._insert(QueryDBEntry).values, query_values)
                    query_update_values = {c.name: c for c in query_insert_op.excluded if not c.primary_key}
                    query_update_values["last_updated"] = datetime.datetime.utcnow()
                    query_op_on_conflict = query_insert_op.on_conflict_do_update(
                        index_elements=["id"],
                        set_=query_update_values,
                    )
                    await session.execute(query_op_on_conflict)
                    track_values = [dict(base64=entry) async for entry in AsyncIter(tracks, steps=100)]
                    track_inset_op = await asyncio.to_thread(self._insert(TrackDBEntry).values, track_values)
                    track_op_on_conflict = track_inset_op.on_conflict_do_nothing(index_elements=["base64"])
                    await session.execute(track_op_on_conflict)
                    query_tracks_values = [
                        dict(id=query_id, base64=track) async for track in AsyncIter(tracks, steps=100)
                    ]
                    query_tracks_insert_op = await asyncio.to_thread(
                        self._insert(QueryTrackDBEntry).values, query_tracks_values
                    )
                    query_tracks_op_on_conflict = query_tracks_insert_op.on_conflict_do_update(
                        index_elements=["id", "base64"], set_=dict(base64=query_tracks_insert_op.excluded.base64)
                    )
                    await session.execute(query_tracks_op_on_conflict)

    async def get_query(self, query_id: str) -> dict | None:
        async with self.session as session:
            result = await session.execute(
                select(QueryDBEntry)
                .select_from(QueryDBEntry)
                .join(QueryTrackDBEntry)
                .where(QueryDBEntry.id == query_id)
            )
            result = result.scalars().first()
            if result:
                return result.as_dict()
