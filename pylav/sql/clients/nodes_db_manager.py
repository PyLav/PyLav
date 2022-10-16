from __future__ import annotations

from typing import TYPE_CHECKING

import pylav.sql.tables.nodes
from pylav._logging import getLogger
from pylav.constants import BUNDLED_NODES_IDS, BUNDLED_NODES_IDS_HOST_MAPPING, PYLAV_BUNDLED_NODES_SETTINGS
from pylav.sql.models import NodeModel, NodeModelMock

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("PyLav.NodeConfigManager")


class NodeConfigManager:
    __slots__ = ("_client", "currently_in_db")

    def __init__(self, client: Client):
        self._client = client
        self.currently_in_db = {
            self._client.bot.user.id,
        }

    @property
    def client(self) -> Client:
        return self._client

    def bundled_node_config(self) -> NodeModel:
        return NodeModel(id=self._client.bot.user.id)

    def get_node_config(self, node_id: int) -> NodeModel:
        if node_id not in BUNDLED_NODES_IDS:
            node = NodeModel(id=node_id)
        else:
            node = NodeModelMock(id=node_id, data=PYLAV_BUNDLED_NODES_SETTINGS[BUNDLED_NODES_IDS_HOST_MAPPING[node_id]])
        self.currently_in_db.add(node.id)
        return node

    async def get_all_unmanaged_nodes(self, dedupe: bool = True) -> list[NodeModel]:
        model_list = [
            NodeModel(**node)
            for node in await pylav.sql.tables.nodes.NodeRow.select(pylav.sql.tables.nodes.NodeRow.id)
            .where(
                (pylav.sql.tables.nodes.NodeRow.managed == False)
                & (pylav.sql.tables.nodes.NodeRow.id.not_in(BUNDLED_NODES_IDS))
            )
            .output(nested=True, load_json=True)
        ]
        new_model_list = list(set(model_list)) if dedupe else model_list
        for n in new_model_list:
            self.currently_in_db.add(n.id)
        return new_model_list

    async def get_all_nodes(self) -> list[NodeModel]:
        model_list = await self.get_all_unmanaged_nodes(dedupe=True)
        if mn := self.bundled_node_config():
            model_list.append(mn)
        return model_list

    async def get_bundled_node_config(self) -> NodeModel | None:
        response = (
            await pylav.sql.tables.nodes.NodeRow.select(pylav.sql.tables.nodes.NodeRow.id)
            .where(
                (pylav.sql.tables.nodes.NodeRow.id == self._client.bot.user.id)
                & (pylav.sql.tables.nodes.NodeRow.managed is True)
            )
            .first()
        )
        return NodeModel(**response) if response else None

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
        await node.bulk_update(
            host=host,
            port=port,
            password=password,
            name=name,
            resume_key=resume_key,
            resume_timeout=resume_timeout,
            reconnect_attempts=reconnect_attempts,
            ssl=ssl,
            search_only=search_only,
            managed=managed,
            extras=extras,
            disabled_sources=disabled_sources,
            yaml=yaml,
        )
        return node

    async def delete(self, node_id: int) -> None:
        if node_id == self._client.bot.user.id:
            raise ValueError("Cannot delete bundled node")
        await self.get_node_config(node_id=node_id).delete()

    @staticmethod
    async def count() -> int:
        """Return the number of unbundled nodes in the database."""
        return await pylav.sql.tables.nodes.NodeRow.count().where(
            pylav.sql.tables.nodes.NodeRow.id.not_in(BUNDLED_NODES_IDS)
        )
