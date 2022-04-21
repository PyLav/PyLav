from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from pylav.exceptions import EntryNotFoundError
from pylav.sql.models import NodeModel
from pylav.sql.tables import NodeRow
from pylav.utils.built_in_node import NODE_DEFAULT_SETTINGS

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("red.PyLink.LibConfigManager")


class NodeConfigManager:
    def __init__(self, client: Client):
        self._client = client
        self._bundled = NodeModel(
            **{
                "id": 0,
                "ssl": False,
                "reconnect_attempts": 3,
                "search_only": False,
                "extras": NODE_DEFAULT_SETTINGS,
                "name": "PyLavManagedNode",
            }
        )

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    async def get_node_config(node_id: str) -> NodeModel:
        node = await NodeRow.select().output(load_json=True).where(NodeRow.id == node_id).first()
        if not node:
            raise EntryNotFoundError(f"Node with id {node_id} not found")
        return NodeModel(**node)

    async def get_bundled_node_config(self) -> NodeModel:
        node = (
            await NodeRow.objects()
            .output(load_json=True)
            .get_or_create(NodeRow.id == 0, defaults=self._bundled.to_dict())
        )
        self._bundled = NodeModel(**node.to_dict())
        return self._bundled
