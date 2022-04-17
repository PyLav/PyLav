from __future__ import annotations

import asyncio
import pathlib
from typing import TYPE_CHECKING

import ujson
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from pylav._config import CONFIG_DIR
from pylav.config.built_in_node import NODE_DEFAULT_SETTINGS
from pylav.config.models import Base, NodeConfigEntry

if TYPE_CHECKING:
    from pylav.client import Client


class ConfigManager:
    def __init__(self, client: Client, config_folder: pathlib.Path = CONFIG_DIR, sql_connection_string: str = None):
        __database_folder: pathlib.Path = config_folder
        __default_db_name: pathlib.Path = __database_folder / "config.db"
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

    async def initialize(self):
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
        await self._engine.dispose()

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()

    async def get_managed_node_config(self) -> dict | None:
        query = select(NodeConfigEntry).where(NodeConfigEntry.node_id == 0)
        async with self.session as session:
            result = await session.execute(query)
            result = result.scalars().first()
            if result:
                return result.as_dict()

    async def create_bundled_node(self):
        if node := await self.get_managed_node_config():
            return node
        async with self.session as session:
            async with session.begin():
                node_values = [
                    dict(
                        node_id=0,
                        ssl=False,
                        reconnect_attempts=3,
                        search_only=False,
                        extras=NODE_DEFAULT_SETTINGS,
                        name="PyLavManagedNode",
                    )
                ]
                insert_op = await asyncio.to_thread(self._insert(NodeConfigEntry).values, node_values)
                update_update_values = {c.name: c for c in insert_op.excluded if not c.primary_key}
                node_op_on_conflict = insert_op.on_conflict_do_update(
                    index_elements=["node_id"],
                    set_=update_update_values,
                )
                await session.execute(node_op_on_conflict)
        return node_values[0]
