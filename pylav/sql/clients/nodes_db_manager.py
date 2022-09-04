from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from pylav._logging import getLogger
from pylav.constants import BUNDLED_NODES_IDS
from pylav.sql import tables
from pylav.sql.models import NodeModel

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("PyLav.NodeConfigManager")


class NodeConfigManager:
    def __init__(self, client: Client):
        self._client = client
        self.currently_in_db = {
            self._client.bot.user.id,
        }

    @property
    def client(self) -> Client:
        return self._client

    @lru_cache(maxsize=1)
    def bundled_node_config(self) -> NodeModel:
        return NodeModel(id=self._client.bot.user.id)

    @lru_cache(maxsize=64)
    def get_node_config(self, node_id: int) -> NodeModel:
        node = NodeModel(id=node_id)
        self.currently_in_db.add(node.id)
        return node

    async def get_all_unamanaged_nodes(self, dedupe: bool = True) -> list[NodeModel]:
        model_list = [
            NodeModel(**node)
            for node in await tables.NodeRow.select(tables.NodeRow.id)
            .output(load_json=True)
            .where(tables.NodeRow.managed == False)  # noqa: E712
        ]
        new_model_list = list(set(model_list)) if dedupe else model_list
        for n in new_model_list:
            self.currently_in_db.add(n.id)
        return new_model_list

    async def get_all_nodes(self) -> list[NodeModel]:
        model_list = [
            NodeModel(**node)
            for node in await tables.NodeRow.select(tables.NodeRow.id)
            .output(load_json=True)
            .where(tables.NodeRow.managed == False)
        ]
        for n in model_list:
            self.currently_in_db.add(n.id)
        if mn := self.bundled_node_config():
            model_list.append(mn)
        return model_list

    async def get_bundled_node_config(self) -> NodeModel | None:
        managed_node = (
            await tables.NodeRow.select(tables.NodeRow.id)
            .output(load_json=True)
            .where((tables.NodeRow.id == self._client.bot.user.id) & (tables.NodeRow.managed == True))
            .first()
        )
        if managed_node:
            return NodeModel(**managed_node)

    async def update_node(
        self,
        host: str,
        port: int,
        password: str,
        unique_identifier: int,
        resume_key: str = None,
        resume_timeout: int = 60,
        name: str = None,
        reconnect_attempts: int = -1,
        ssl: bool = False,
        search_only: bool = False,
        managed: bool = False,
        extras: dict = None,
        yaml: dict = None,
        disabled_sources: list[str] = None,
    ) -> NodeModel:

        """
        Add a new node to the database.

        Parameters
        ----------
        host: str
            The host of the node.
        port: int
            The port of the node.
        password: str
            The password of the node.
        unique_identifier: int
            The unique identifier of the node.
        name: str
            The name of the node.
        resume_key: str
            The resume key of the node.
        resume_timeout: int
            The resume timeout of the node.
        reconnect_attempts: int
            The reconnect attempts of the node.
        ssl: bool
            Whether the node is using ssl.
        search_only: bool
            Whether the node is search only.
        managed: bool
            Whether the node is managed.
        extras: dict
            The extras of the node.
        disabled_sources: list[str]
            The disabled sources of the node.
        yaml: dict
            The yaml of the node.
        """

        node = NodeModel(id=unique_identifier)
        self.currently_in_db.add(node.id)
        async with tables.DB.transaction():
            await node.update_ssl(ssl)
            await node.update_reconnect_attempts(reconnect_attempts)
            await node.update_search_only(search_only)
            await node.update_resume_key(resume_key)
            await node.update_resume_timeout(resume_timeout)
            await node.update_managed(managed)

            if name is not None:
                await node.update_name(name)
            if disabled_sources is not None:
                await node.update_disabled_sources(disabled_sources)
            if extras is not None:
                await node.update_extras(extras)
            yaml = yaml or {"server": {}, "lavalink": {"server": {}}}
            yaml["server"]["address"] = host  # type: ignore
            yaml["server"]["port"] = port  # type: ignore
            yaml["lavalink"]["server"]["password"] = password
            await node.update_yaml(yaml)
            self.currently_in_db.add(node.id)
        return node

    async def delete(self, node_id: int) -> None:
        if node_id == self._client.bot.user.id:
            raise ValueError("Cannot delete bundled node")
        await self.get_node_config(node_id=node_id).delete()

    async def count(self) -> int:
        """Return the number of unbundled nodes in the database."""
        return await tables.NodeRow.count().where(tables.NodeRow.id.not_in(BUNDLED_NODES_IDS))
