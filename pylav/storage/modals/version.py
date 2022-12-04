from __future__ import annotations

import typing
from dataclasses import dataclass

from packaging.version import Version, parse

from pylav.storage.database.caching import CachedSingletonByKey
from pylav.storage.database.caching.decodators import maybe_cached
from pylav.storage.database.caching.model import CachedModel
from pylav.storage.database.tables.version import BotVersionRow


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class BotVersion(CachedModel, metaclass=CachedSingletonByKey):
    id: int

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

    async def update_version(self, version: Version | str):
        """Update the version of the bot in the database"""
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await BotVersionRow.raw(
            """
            INSERT INTO version (bot, version)
            VALUES ({}, {})
            ON CONFLICT (bot)
            DO UPDATE SET version = EXCLUDED.version
            """,
            self.id,
            str(version),
        )
        await self.invalidate_cache(self.fetch_version)
