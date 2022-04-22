from __future__ import annotations

from typing import TYPE_CHECKING

from red_commons.logging import getLogger

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
        self.currently_in_db = {
            0,
        }

    @property
    def client(self) -> Client:
        return self._client

    @property
    def bundled_node_config(self) -> NodeModel:
        return self._bundled

    async def get_node_config(self, node_id: int) -> NodeModel:
        node = await NodeRow.select().output(load_json=True).where(NodeRow.id == node_id).first()
        if not node:
            raise EntryNotFoundError(f"Node with id {node_id} not found")
        model = NodeModel(**node)
        self.currently_in_db.add(model.id)
        return model

    async def get_all_unamanaged_nodes(self) -> list[NodeModel]:
        model_list = [
            NodeModel(**node.to_dict())
            for node in await NodeRow.objects().output(load_json=True).where(NodeRow.id != 0)
        ]
        for n in model_list:
            self.currently_in_db.add(n.id)

        return model_list

    async def get_bundled_node_config(self) -> NodeModel:
        node = (
            await NodeRow.objects()
            .output(load_json=True)
            .get_or_create(NodeRow.id == 0, defaults=self._bundled.to_dict())
        )
        self._bundled = NodeModel(**node.to_dict())
        return self._bundled

    async def add_node(
        self,
        host: str,
        port: int,
        password: str,
        unique_identifier: int,
        resume_key: str = None,
        resume_timeout: int = 60,
        name: str = None,
        reconnect_attempts: int = 3,
        ssl: bool = False,
        search_only: bool = False,
    ) -> NodeModel:
        if unique_identifier in self.currently_in_db:
            return await self.get_node_config(unique_identifier)

        data = {
            "extras": {"server": {}, "lavalink": {"server": {}}},
            "id": unique_identifier,
            "ssl": ssl,
            "reconnect_attempts": reconnect_attempts,
            "search_only": search_only,
            "name": name,
        }
        data["extras"]["server"]["host"] = host
        data["extras"]["server"]["host"] = port
        data["extras"]["lavalink"]["server"]["password"] = password
        data["extras"]["resume_timeout"] = resume_timeout
        data["extras"]["resume_key"] = resume_key
        node = NodeModel(**data)
        await node.save()
        self.currently_in_db.add(node.id)
        return node

    async def update_node(
        self,
        host: str,
        port: int,
        password: str,
        unique_identifier: int,
        resume_key: str = None,
        resume_timeout: int = 60,
        name: str = None,
        reconnect_attempts: int = 3,
        ssl: bool = False,
        search_only: bool = False,
        extras: dict = None,
    ) -> NodeModel:
        data = {
            "extras": {"server": {}, "lavalink": {"server": {}}},
            "id": unique_identifier,
            "ssl": ssl,
            "reconnect_attempts": reconnect_attempts,
            "search_only": search_only,
            "name": name,
        }
        if extras:
            data["extras"] = extras
        data["extras"]["server"]["host"] = host  # type: ignore
        data["extras"]["server"]["port"] = port  # type: ignore
        data["extras"]["lavalink"]["server"]["password"] = password
        if unique_identifier != 0:
            data["extras"]["resume_timeout"] = resume_timeout  # type: ignore
            data["extras"]["resume_key"] = resume_key  # type: ignore
        node = NodeModel(**data)
        await node.save()
        self.currently_in_db.add(node.id)
        return node

    async def delete(self, node_id: int) -> None:
        if node_id == 0:
            raise ValueError("Cannot delete bundled node")
        await NodeRow.delete().where(NodeRow.id == node_id)
        self.currently_in_db.discard(node_id)
