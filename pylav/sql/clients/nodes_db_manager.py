from __future__ import annotations

from typing import TYPE_CHECKING

from pylav._logging import getLogger
from pylav.exceptions import EntryNotFoundError
from pylav.sql import tables
from pylav.sql.models import NodeModel
from pylav.utils.built_in_node import NODE_DEFAULT_SETTINGS

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

    @property
    async def bundled_node_config(self) -> NodeModel:
        return await self.get_bundled_node_config()

    async def get_node_config(self, node_id: int) -> NodeModel:
        node = await tables.NodeRow.select().output(load_json=True).where(tables.NodeRow.id == node_id).first()
        if not node:
            raise EntryNotFoundError(f"Node with id {node_id} not found")
        model = NodeModel(**node)
        self.currently_in_db.add(model.id)
        return model

    async def get_all_unamanaged_nodes(self) -> list[NodeModel]:
        model_list = [
            NodeModel(**node.to_dict())
            for node in await tables.NodeRow.objects()
            .output(load_json=True)
            .where(tables.NodeRow.managed == False)  # noqa: E712
        ]
        for n in model_list:
            self.currently_in_db.add(n.id)

        return model_list

    async def get_all_nodes(self) -> list[NodeModel]:
        model_list = [
            NodeModel(**node.to_dict())
            for node in await tables.NodeRow.objects().output(load_json=True).where(tables.NodeRow.managed == False)
        ]
        for n in model_list:
            self.currently_in_db.add(n.id)
        model_list.append(await self.get_bundled_node_config())
        return model_list

    async def get_bundled_node_config(self) -> NodeModel:
        node = (
            await tables.NodeRow.objects()
            .output(load_json=True)
            .get_or_create(
                (tables.NodeRow.id == self._client.bot.user.id) & (tables.NodeRow.managed == True),  # noqa: E712
                defaults={
                    tables.NodeRow.ssl: False,
                    tables.NodeRow.reconnect_attempts: -1,
                    tables.NodeRow.search_only: False,
                    tables.NodeRow.yaml: NODE_DEFAULT_SETTINGS,
                    tables.NodeRow.name: "PyLavManagedNode",
                    tables.NodeRow.managed: True,
                    tables.NodeRow.resume_key: None,
                    tables.NodeRow.resume_timeout: 600,
                    tables.NodeRow.extras: {"max_ram": "2048M"},
                },
            )
        )
        data = node.to_dict()
        if "max_ram" not in data["extras"]:
            data["extras"]["max_ram"] = "2048M"
        return NodeModel(**data)

    async def add_node(
        self,
        host: str,
        port: int,
        password: str,
        unique_identifier: int,
        name: str,
        resume_key: str = None,
        resume_timeout: int = 60,
        reconnect_attempts: int = -1,
        ssl: bool = False,
        search_only: bool = False,
        managed: bool = False,
        extras: dict = None,
        disabled_sources: list[str] = None,
        yaml: dict = None,
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
            disabled_sources=disabled_sources or [],
            extras=extras or {},
        )
        data["yaml"]["server"]["address"] = host  # type: ignore
        data["yaml"]["server"]["port"] = port  # type: ignore
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
        reconnect_attempts: int = -1,
        ssl: bool = False,
        search_only: bool = False,
        managed: bool = False,
        extras: dict = None,
        yaml: dict = None,
        disabled_sources: list[str] = None,
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
            disabled_sources=disabled_sources or [],
            extras=extras or {},
        )
        data["yaml"]["server"]["address"] = host  # type: ignore
        data["yaml"]["server"]["port"] = port  # type: ignore
        data["yaml"]["lavalink"]["server"]["password"] = password
        node = NodeModel(**data)
        await node.save()
        self.currently_in_db.add(node.id)
        return node

    async def delete(self, node_id: int) -> None:
        if node_id == self._client.bot.user.id:
            raise ValueError("Cannot delete bundled node")
        await tables.NodeRow.delete().where(
            (tables.NodeRow.id == node_id) & (tables.NodeRow.managed != True)
        )  # noqa: E712
        self.currently_in_db.discard(node_id)
