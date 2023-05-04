from __future__ import annotations

from dataclasses import dataclass, field
from typing import NotRequired

from pylav.constants.builtin_nodes import BUNDLED_NODES_IDS_HOST_MAPPING
from pylav.constants.node_features import SUPPORTED_FEATURES, SUPPORTED_SOURCES
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.nodes import Sessions
from pylav.type_hints.dict_typing import JSON_DICT_TYPE


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True)
class NodeMock(CachedModel):
    id: int
    data: JSON_DICT_TYPE

    session_id: NotRequired[str | None] = field(repr=False, init=False, hash=None, compare=False, default=...)

    def __post_init__(self):
        self.session_id = ...

    def get_cache_key(self) -> str:
        return f"{self.id}"

    @staticmethod
    async def exists() -> bool:
        """Check if the node exists in the database.

        Returns
        -------
        bool
            Whether the node exists in the database.
        """
        return False

    async def delete(self) -> None:
        """Delete the node from the database"""

    async def fetch_all(self) -> JSON_DICT_TYPE:
        return {"id": self.id, **self.data}

    async def fetch_name(self) -> str:
        """Fetch the node from the database.

        Returns
        -------
        ste
            The node's name.
        """
        return self.data["name"]

    async def update_name(self, name: str) -> None:
        """Update the node's name in the database"""
        self.data["name"] = name

    async def fetch_ssl(self) -> bool:
        """Fetch the node's ssl setting from the database.

        Returns
        -------
        bool
            The node's ssl setting.
        """
        return self.data["ssl"]

    async def update_ssl(self, ssl: bool) -> None:
        """Update the node's ssl setting in the database"""
        self.data["ssl"] = ssl

    async def fetch_resume_timeout(self) -> int:
        """Fetch the node's resume timeout from the database.

        Returns
        -------
        int
            The node's resume timeout.
        """
        return self.data["resume_timeout"]

    async def update_resume_timeout(self, resume_timeout: int) -> None:
        """Update the node's resume timeout in the database"""
        self.data["resume_timeout"] = resume_timeout

    async def fetch_reconnect_attempts(self) -> int:
        """Fetch the node's reconnect attempts from the database.

        Returns
        -------
        int
            The node's reconnect attempts.
        """
        return self.data["reconnect_attempts"]

    async def update_reconnect_attempts(self, reconnect_attempts: int) -> None:
        """Update the node's reconnect attempts in the database"""
        self.data["reconnect_attempts"] = reconnect_attempts

    async def fetch_search_only(self) -> bool:
        """Fetch the node's search only setting from the database.

        Returns
        -------
        bool
            The node's search only setting.
        """
        return self.data["search_only"]

    async def update_search_only(self, search_only: bool) -> None:
        """Update the node's search only setting in the database"""
        self.data["search_only"] = search_only

    async def fetch_managed(self) -> bool:
        """Fetch the node's managed setting from the database.

        Returns
        -------
        bool
            The node's managed setting.
        """
        return self.data["managed"]

    async def update_managed(self, managed: bool) -> None:
        """Update the node's managed setting in the database"""
        self.data["managed"] = managed

    async def fetch_extras(self) -> JSON_DICT_TYPE:
        """Fetch the node's extras from the database.

        Returns
        -------
        dict
            The node's extras.
        """
        return self.data["extras"]

    async def update_extras(self, extras: JSON_DICT_TYPE) -> None:
        """Update the node's extras in the database"""
        self.data["extras"] = extras

    async def fetch_yaml(self) -> JSON_DICT_TYPE:
        """Fetch the node's yaml from the database.

        Returns
        -------
        dict
            The node's yaml.
        """
        return self.data["yaml"]

    async def update_yaml(self, yaml_data: JSON_DICT_TYPE) -> None:
        """Update the node's yaml in the database"""
        self.data["yaml"] = yaml_data

    async def fetch_disabled_sources(self) -> list[str]:
        """Fetch the node's disabled sources from the database.

        Returns
        -------
        list[str]
            The node's disabled sources.
        """
        return self.data["disabled_sources"]

    async def update_disabled_sources(self, disabled_sources: list[str]) -> None:
        """Update the node's disabled sources in the database"""
        source = set(map(str.strip, map(str.lower, disabled_sources)))
        intersection = list(source & SUPPORTED_SOURCES.union(SUPPORTED_FEATURES))
        self.data["disabled_sources"] = intersection

    async def add_to_disabled_sources(self, source: str) -> None:
        """Add a source to the node's disabled sources in the database"""
        data = set(self.data["disabled_sources"])
        data.update([source])
        self.data["disabled_sources"] = list(data)

    async def remove_from_disabled_sources(self, source: str) -> None:
        """Remove a source from the node's disabled sources in the database"""
        data = set(self.data["disabled_sources"])
        data.discard(source)
        self.data["disabled_sources"] = list(data)

    async def bulk_add_to_disabled_sources(self, sources: list[str]) -> None:
        """Add sources to the node's disabled sources in the database"""
        source = set(map(str.strip, map(str.lower, [sources])))
        source.update(self.data["disabled_sources"])
        intersection = list(source & SUPPORTED_SOURCES.union(SUPPORTED_FEATURES))
        self.data["disabled_sources"] = intersection

    async def bulk_remove_from_disabled_sources(self, sources: list[str]) -> None:
        """Remove sources from the node's disabled sources in the database"""
        if not sources:
            return
        for source in sources:
            await self.remove_from_disabled_sources(source)

    async def get_connection_args(self) -> dict[str, int | str | bool | None, list[str]]:
        """Get the connection args for the node.

        Returns
        -------
        dict
            The connection args.
        """
        data = await self.fetch_all()
        if self.id in BUNDLED_NODES_IDS_HOST_MAPPING:
            data["yaml"]["lavalink"]["server"]["password"] = self.client._user_id
        return {
            "unique_identifier": self.id,
            "host": data["yaml"]["server"]["address"],
            "port": data["yaml"]["server"]["port"],
            "password": data["yaml"]["lavalink"]["server"]["password"],
            "name": data["name"],
            "ssl": data["ssl"],
            "reconnect_attempts": data["reconnect_attempts"],
            "search_only": data["search_only"],
            "resume_timeout": data["resume_timeout"],
            "disabled_sources": data["disabled_sources"],
            "managed": data["managed"],
            "temporary": True,
        }

    @classmethod
    async def create_managed(cls, identifier: int) -> None:
        """Create the player in the database"""

    async def fetch_session(self) -> str | None:
        """Fetch the node's session from the database.

        Returns
        -------
        str | None
            The node's session.
        """

        if self.session_id is ...:
            session = (
                await Sessions.select(Sessions.id)
                .where((Sessions.node == self.id) & (Sessions.bot == self.client.bot.user.id))  # noqa: E712
                .first()
                .output(load_json=True)
            )
            if session and (sid := session.get("id")):
                self.session_id = sid
                return self.session_id
            self.session_id = None
        return self.data.get("session", None)

    async def update_session(self, session: str | None) -> None:
        """Update the node's session in the database"""
        self.data["session"] = session
        self.session_id = session
        await Sessions.insert(Sessions(id=session, node=self.id, bot=self.client.bot.user.id)).on_conflict(
            action="DO UPDATE",
            target=(Sessions.node, Sessions.bot),
            values=[Sessions.id],
        )
