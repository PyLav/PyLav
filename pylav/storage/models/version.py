from __future__ import annotations

import typing
from dataclasses import dataclass

from packaging.version import Version, parse

from pylav.helpers.singleton import SingletonCachedByKey
from pylav.storage.database.cache.decodators import maybe_cached
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.version import BotVersionRow


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class BotVersion(CachedModel, metaclass=SingletonCachedByKey):
    """A class to represent the version of the bot in the database"""

    id: int

    def get_cache_key(self) -> str:
        """Get the cache key for the bot version."""
        return f"{self.id}"

    @maybe_cached
    async def fetch_version(self) -> Version:
        """Fetch the version of the bot from the database"""
        data = (
            await BotVersionRow.select(BotVersionRow.version)
            .where(BotVersionRow.bot == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return typing.cast(Version, parse(data["version"] if data else BotVersionRow.version.default))

    async def update_version(self, version: Version | str) -> None:
        """Update the version of the bot in the database"""
        await BotVersionRow.insert(BotVersionRow(bot=self.id, version=str(version))).on_conflict(
            action="DO UPDATE", target=BotVersionRow.bot, values=[BotVersionRow.version]
        )
