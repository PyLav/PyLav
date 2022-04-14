from __future__ import annotations

import pathlib

import ujson
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from pylav._config import LIB_CONFIG_FOLDER
from pylav.player_state.models import Base


class PlayerStateManager:
    __database_folder: pathlib.Path = LIB_CONFIG_FOLDER
    __default_db_name: pathlib.Path = __database_folder / "players.db"

    def __init__(self):
        self._engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.__default_db_name}", json_deserializer=ujson.loads, json_serializer=ujson.dumps
        )
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
