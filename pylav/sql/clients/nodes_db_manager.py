from __future__ import annotations

from typing import TYPE_CHECKING

from red_commons.logging import getLogger

from pylav.exceptions import EntryNotFoundError
from pylav.sql.models import NodeModel
from pylav.sql.tables import NodeRow
from pylav.utils.built_in_node import NODE_DEFAULT_SETTINGS

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("red.PyLink.NodeConfigManager")


class NodeConfigManager:
    def __init__(self, client: Client):
        self._client = client
        self.currently_in_db = {
            self._client.bot.user.id,
        }

    @property
    def client(self) -> Client:
        return self._client

    @property
    async def bundled_node_config(self) -> NodeModel:
        return await self.get_bundled_node_config()

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
            for node in await NodeRow.objects().output(load_json=True).where(NodeRow.managed == False)  # noqa: E712
        ]
        for n in model_list:
            self.currently_in_db.add(n.id)

        return model_list

    async def get_bundled_node_config(self) -> NodeModel:
        node = (
            await NodeRow.objects()
            .output(load_json=True)
            .get_or_create(
                (NodeRow.id == self._client.bot.user.id) & (NodeRow.managed == True),  # noqa: E712
                defaults={
                    NodeRow.ssl: False,
                    NodeRow.reconnect_attempts: 3,
                    NodeRow.search_only: False,
                    NodeRow.yaml: NODE_DEFAULT_SETTINGS,
                    NodeRow.name: "PyLavManagedNode",
                    NodeRow.managed: True,
                    NodeRow.resume_key: None,
                    NodeRow.resume_timeout: 600,
                    NodeRow.extras: {},
                },
            )
        )
        return NodeModel(**node.to_dict())

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
        managed: bool = False,
        extras: dict = None,
        yaml: dict = None,
    ) -> NodeModel:
        if unique_identifier in self.currently_in_db:
            return await self.get_node_config(unique_identifier)

        data = dict(
            yaml=yaml or {"server": {}, "lavalink": {"server": {}}},
            id=unique_identifier,
            ssl=ssl,
            reconnect_attempts=reconnect_attempts,
            search_only=search_only,
            resume_key=resume_key,
            resume_timeout=resume_timeout,
            managed=managed,
            name=name,
            extras=extras or {},
        )
        data["yaml"]["server"]["host"] = host  # type: ignore
        data["yaml"]["server"]["host"] = port  # type: ignore
        data["yaml"]["lavalink"]["server"]["password"] = password

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
        managed: bool = False,
        extras: dict = None,
        yaml: dict = None,
    ) -> NodeModel:
        data = dict(
            yaml=yaml or {"server": {}, "lavalink": {"server": {}}},
            id=unique_identifier,
            ssl=ssl,
            reconnect_attempts=reconnect_attempts,
            search_only=search_only,
            resume_key=resume_key,
            resume_timeout=resume_timeout,
            managed=managed,
            name=name,
            extras=extras or {},
        )
        data["yaml"]["server"]["host"] = host  # type: ignore
        data["yaml"]["server"]["host"] = port  # type: ignore
        data["yaml"]["lavalink"]["server"]["password"] = password
        node = NodeModel(**data)
        await node.save()
        self.currently_in_db.add(node.id)
        return node

    async def delete(self, node_id: int) -> None:
        if node_id == self._client.bot.user.id:
            raise ValueError("Cannot delete bundled node")
        await NodeRow.delete().where((NodeRow.id == node_id) & (NodeRow.managed != True))  # noqa: E712
        self.currently_in_db.discard(node_id)
