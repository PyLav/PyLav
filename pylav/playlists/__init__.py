from __future__ import annotations

import asyncio
import contextlib
import datetime
import pathlib

import ujson
from sqlalchemy import and_, event, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from pylav._config import CONFIG_DIR
from pylav.client import Client
from pylav.playlists.models import Base, PlaylistDBEntry, PlaylistTrackDBEntry, TrackDBEntry
from pylav.utils import AsyncIter


class PlaylistManager:
    def __init__(self, client: Client, config_folder: pathlib.Path = CONFIG_DIR, sql_connection_string: str = None):
        __database_folder: pathlib.Path = config_folder
        __default_db_name: pathlib.Path = __database_folder / "players.db"
        if not sql_connection_string or "sqlite+aiosqlite:///" in sql_connection_string:
            sql_connection_string = f"sqlite+aiosqlite:///{__default_db_name}"
        self._engine = create_async_engine(
            sql_connection_string, json_deserializer=ujson.loads, json_serializer=ujson.dumps
        )
        self._client = client
        self._session = sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)
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

    async def upsert_playlists(self, playlists: list[dict]):
        async with self.session as session:
            async with session.begin():
                async for playlist in AsyncIter(playlists):
                    tracks = playlist.pop("tracks")
                    playlist_values = [
                        dict(
                            id=playlist["id"],
                            scope=playlist["scope"],
                            scope_id=playlist["scope_id"],
                            author=playlist["author"],
                            name=playlist["name"],
                            url=playlist["url"],
                        )
                    ]
                    playlist_op = await asyncio.to_thread(insert(PlaylistDBEntry).values, playlist_values)
                    playlist_op_on_conflict = playlist_op.on_conflict_do_update(
                        index_elements=["id"],
                        set_=dict(
                            scope=playlist_op.excluded.scope,
                            scope_id=playlist_op.excluded.scope_id,
                            author=playlist_op.excluded.author,
                            name=playlist_op.excluded.name,
                            url=playlist_op.excluded.url,
                            last_updated=datetime.datetime.utcnow(),
                        ),
                    )
                    await session.execute(playlist_op_on_conflict)
                    track_values = [dict(base64=entry) async for entry in AsyncIter(tracks)]
                    track_op = await asyncio.to_thread(insert(TrackDBEntry).values, track_values)
                    track_op_on_conflict = track_op.on_conflict_do_nothing(index_elements=["base64"])
                    await session.execute(track_op_on_conflict)
                    playlist_tracks_values = [
                        dict(id=playlist_values[0]["id"], base64=track["base64"])
                        async for track in AsyncIter(track_values, steps=1000)
                    ]
                    playlist_tracks_op = await asyncio.to_thread(
                        insert(PlaylistTrackDBEntry).values, playlist_tracks_values
                    )
                    playlist_tracks_op_on_conflict = playlist_tracks_op.on_conflict_do_update(
                        index_elements=["id", "base64"], set_=dict(base64=playlist_tracks_op.excluded.base64)
                    )
                    await session.execute(playlist_tracks_op_on_conflict)

    async def get_playlist(self, playlist_id_or_name: int | str) -> dict | None:
        filter_list = [PlaylistDBEntry.name == playlist_id_or_name]
        with contextlib.suppress(ValueError):
            playlist_id = int(playlist_id_or_name)
            filter_list.append(PlaylistDBEntry.id == playlist_id)
        query = select(PlaylistDBEntry).select_from(PlaylistDBEntry).join(PlaylistTrackDBEntry).where(or_(*filter_list))
        async with self.session as session:
            result = await session.execute(query)
            result = result.scalars().first()
            if result:
                return result.as_dict()

    async def get_playlists(
        self,
        eq_name: str | None = None,
        eq_id: int | None = None,
        scope: int | None = None,
        scope_int: int | None = None,
        author: int | None = None,
    ) -> list[dict]:
        filter_list = []
        if eq_id is not None:
            filter_list.append(PlaylistDBEntry.id == eq_id)
        if eq_name is not None:
            filter_list.append(PlaylistDBEntry.name == eq_name)
        if scope is not None:
            filter_list.append(PlaylistDBEntry.scope == scope)
        if scope_int is not None:
            filter_list.append(PlaylistDBEntry.scope_id == scope_int)
        if author is not None:
            filter_list.append(PlaylistDBEntry.author == author)
        if not filter_list:
            query = select(PlaylistDBEntry).select_from(PlaylistDBEntry).join(PlaylistTrackDBEntry)
        else:
            query = (
                select(PlaylistDBEntry)
                .select_from(PlaylistDBEntry)
                .join(PlaylistTrackDBEntry)
                .where(and_(*filter_list))
            )
        async with self.session as session:
            result = await session.execute(query)
            result = result.scalars().all()
            if result:
                return [row.as_dict() for row in result]
        return []
