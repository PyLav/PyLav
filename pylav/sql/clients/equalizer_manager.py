from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import discord

import pylav.sql.tables.equalizers
from pylav._logging import getLogger
from pylav.exceptions import EntryNotFoundError
from pylav.sql.models import EqualizerModel
from pylav.types import BotT
from pylav.utils import AsyncIter

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("PyLav.EqualizerConfigManager")


class EqualizerConfigManager:
    __slots__ = ("_client",)

    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    async def get_equalizer_by_name(equalizer_name: str, limit: int = None) -> list[EqualizerModel]:
        if limit is None:
            equalizers = (
                await pylav.sql.tables.equalizers.EqualizerRow.select()
                .where(pylav.sql.tables.equalizers.EqualizerRow.name.ilike(f"%{equalizer_name.lower()}%"))
                .output(load_json=True, nested=True)
            )
        else:
            equalizers = (
                await pylav.sql.tables.equalizers.EqualizerRow.select()
                .where(pylav.sql.tables.equalizers.EqualizerRow.name.ilike(f"%{equalizer_name.lower()}%"))
                .limit(limit)
            ).output(load_json=True, nested=True)

        if not equalizers:
            raise EntryNotFoundError(f"Equalizer with name {equalizer_name} not found")
        return [EqualizerModel(**equalizer) for equalizer in equalizers]

    @staticmethod
    async def get_equalizer_by_id(equalizer_id: int | str) -> EqualizerModel:
        try:
            equalizer_id = int(equalizer_id)
        except ValueError as e:
            raise EntryNotFoundError(f"Equalizer with id {equalizer_id} not found") from e
        equalizer = (
            await pylav.sql.tables.equalizers.EqualizerRow.select()
            .where(pylav.sql.tables.equalizers.EqualizerRow.id == equalizer_id)
            .first()
            .output(load_json=True, nested=True)
        )
        if not equalizer:
            raise EntryNotFoundError(f"Equalizer with ID {equalizer_id} not found")
        return EqualizerModel(**equalizer)

    async def get_equalizer_by_name_or_id(
        self, equalizer_name_or_id: int | str, limit: int = None
    ) -> list[EqualizerModel]:
        try:
            return [await self.get_equalizer_by_id(equalizer_name_or_id)]
        except EntryNotFoundError:
            return await self.get_equalizer_by_name(equalizer_name_or_id, limit=limit)

    @staticmethod
    async def get_equalizers_by_author(author: int) -> list[EqualizerModel]:
        equalizers = (
            await pylav.sql.tables.equalizers.EqualizerRow.select()
            .where(pylav.sql.tables.equalizers.EqualizerRow.author == author)
            .output(load_json=True, nested=True)
        )
        if not equalizers:
            raise EntryNotFoundError(f"Equalizer with author {author} not found")
        return [EqualizerModel(**equalizer) for equalizer in equalizers]

    @staticmethod
    async def get_equalizers_by_scope(scope: int) -> list[EqualizerModel]:
        equalizers = (
            await pylav.sql.tables.equalizers.EqualizerRow.select()
            .where(pylav.sql.tables.equalizers.EqualizerRow.scope == scope)
            .output(load_json=True, nested=True)
        )
        if not equalizers:
            raise EntryNotFoundError(f"Equalizer with scope {scope} not found")
        return [EqualizerModel(**equalizer) for equalizer in equalizers]

    @staticmethod
    async def get_all_equalizers() -> AsyncIterator[EqualizerModel]:
        for entry in await pylav.sql.tables.equalizers.EqualizerRow.select().output(load_json=True, nested=True):
            yield EqualizerModel(**entry)

    @staticmethod
    async def create_or_update_equalizer(
        id: int,
        scope: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float = 0.0,
        band_40: float = 0.0,
        band_63: float = 0.0,
        band_100: float = 0.0,
        band_160: float = 0.0,
        band_250: float = 0.0,
        band_400: float = 0.0,
        band_630: float = 0.0,
        band_1000: float = 0.0,
        band_1600: float = 0.0,
        band_2500: float = 0.0,
        band_4000: float = 0.0,
        band_6300: float = 0.0,
        band_10000: float = 0.0,
        band_16000: float = 0.0,
    ) -> EqualizerModel:
        values = {
            pylav.sql.tables.equalizers.EqualizerRow.scope: scope,
            pylav.sql.tables.equalizers.EqualizerRow.author: author,
            pylav.sql.tables.equalizers.EqualizerRow.name: name,
            pylav.sql.tables.equalizers.EqualizerRow.description: description,
            pylav.sql.tables.equalizers.EqualizerRow.band_25: band_25,
            pylav.sql.tables.equalizers.EqualizerRow.band_40: band_40,
            pylav.sql.tables.equalizers.EqualizerRow.band_63: band_63,
            pylav.sql.tables.equalizers.EqualizerRow.band_100: band_100,
            pylav.sql.tables.equalizers.EqualizerRow.band_160: band_160,
            pylav.sql.tables.equalizers.EqualizerRow.band_250: band_250,
            pylav.sql.tables.equalizers.EqualizerRow.band_400: band_400,
            pylav.sql.tables.equalizers.EqualizerRow.band_630: band_630,
            pylav.sql.tables.equalizers.EqualizerRow.band_1000: band_1000,
            pylav.sql.tables.equalizers.EqualizerRow.band_1600: band_1600,
            pylav.sql.tables.equalizers.EqualizerRow.band_2500: band_2500,
            pylav.sql.tables.equalizers.EqualizerRow.band_4000: band_4000,
            pylav.sql.tables.equalizers.EqualizerRow.band_6300: band_6300,
            pylav.sql.tables.equalizers.EqualizerRow.band_10000: band_10000,
            pylav.sql.tables.equalizers.EqualizerRow.band_16000: band_16000,
        }
        equalizer = (
            await pylav.sql.tables.equalizers.EqualizerRow.objects()
            .output(load_json=True, nested=True)
            .get_or_create(pylav.sql.tables.equalizers.EqualizerRow.id == id, defaults=values)
        )
        if not equalizer._was_created:
            await pylav.sql.tables.equalizers.EqualizerRow.update(values).where(
                pylav.sql.tables.equalizers.EqualizerRow.id == id
            )
        return EqualizerModel(**equalizer.to_dict())

    @staticmethod
    async def delete_equalizer(equalizer_id: int) -> None:
        await pylav.sql.tables.equalizers.EqualizerRow.delete().where(
            pylav.sql.tables.equalizers.EqualizerRow.id == equalizer_id
        )

    @staticmethod
    async def get_all_equalizers_by_author(author: int) -> AsyncIterator[EqualizerModel]:
        for entry in (
            await pylav.sql.tables.equalizers.EqualizerRow.select()
            .where(pylav.sql.tables.equalizers.EqualizerRow.author == author)
            .output(load_json=True, nested=True)
        ):
            yield EqualizerModel(**entry)

    @staticmethod
    async def get_all_equalizers_by_scope(scope: int) -> AsyncIterator[EqualizerModel]:
        for entry in (
            await pylav.sql.tables.equalizers.EqualizerRow.select()
            .where(pylav.sql.tables.equalizers.EqualizerRow.scope == scope)
            .output(load_json=True, nested=True)
        ):
            yield EqualizerModel(**entry)

    @staticmethod
    async def get_all_equalizers_by_scope_and_author(scope: int, author: int) -> AsyncIterator[EqualizerModel]:
        for entry in (
            await pylav.sql.tables.equalizers.EqualizerRow.select()
            .where(
                pylav.sql.tables.equalizers.EqualizerRow.scope == scope,
                pylav.sql.tables.equalizers.EqualizerRow.author == author,
            )
            .output(load_json=True, nested=True)
        ):
            yield EqualizerModel(**entry)

    async def get_global_equalizers(self) -> AsyncIterator[EqualizerModel]:
        for entry in (
            await pylav.sql.tables.equalizers.EqualizerRow.select()
            .where(pylav.sql.tables.equalizers.EqualizerRow.scope == self._client.bot.user.id)
            .output(load_json=True, nested=True)
        ):  # type: ignore
            yield EqualizerModel(**entry)

    async def create_or_update_global_equalizer(
        self,
        id: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float = 0.0,
        band_40: float = 0.0,
        band_63: float = 0.0,
        band_100: float = 0.0,
        band_160: float = 0.0,
        band_250: float = 0.0,
        band_400: float = 0.0,
        band_630: float = 0.0,
        band_1000: float = 0.0,
        band_1600: float = 0.0,
        band_2500: float = 0.0,
        band_4000: float = 0.0,
        band_6300: float = 0.0,
        band_10000: float = 0.0,
        band_16000: float = 0.0,
    ) -> EqualizerModel:
        return await self.create_or_update_equalizer(
            id=id,
            scope=self._client.bot.user.id,
            author=author,
            name=name,
            description=description,
            band_25=band_25,
            band_40=band_40,
            band_63=band_63,
            band_100=band_100,
            band_160=band_160,
            band_250=band_250,
            band_400=band_400,
            band_630=band_630,
            band_1000=band_1000,
            band_1600=band_1600,
            band_2500=band_2500,
            band_4000=band_4000,
            band_6300=band_6300,
            band_10000=band_10000,
            band_16000=band_16000,
        )

    async def create_or_update_user_equalizer(
        self,
        id: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float = 0.0,
        band_40: float = 0.0,
        band_63: float = 0.0,
        band_100: float = 0.0,
        band_160: float = 0.0,
        band_250: float = 0.0,
        band_400: float = 0.0,
        band_630: float = 0.0,
        band_1000: float = 0.0,
        band_1600: float = 0.0,
        band_2500: float = 0.0,
        band_4000: float = 0.0,
        band_6300: float = 0.0,
        band_10000: float = 0.0,
        band_16000: float = 0.0,
    ) -> EqualizerModel:
        return await self.create_or_update_equalizer(
            id=id,
            scope=author,
            author=author,
            name=name,
            description=description,
            band_25=band_25,
            band_40=band_40,
            band_63=band_63,
            band_100=band_100,
            band_160=band_160,
            band_250=band_250,
            band_400=band_400,
            band_630=band_630,
            band_1000=band_1000,
            band_1600=band_1600,
            band_2500=band_2500,
            band_4000=band_4000,
            band_6300=band_6300,
            band_10000=band_10000,
            band_16000=band_16000,
        )

    async def create_or_update_channel_equalizer(
        self,
        channel: discord.abc.MessageableChannel,
        id: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float = 0.0,
        band_40: float = 0.0,
        band_63: float = 0.0,
        band_100: float = 0.0,
        band_160: float = 0.0,
        band_250: float = 0.0,
        band_400: float = 0.0,
        band_630: float = 0.0,
        band_1000: float = 0.0,
        band_1600: float = 0.0,
        band_2500: float = 0.0,
        band_4000: float = 0.0,
        band_6300: float = 0.0,
        band_10000: float = 0.0,
        band_16000: float = 0.0,
    ) -> EqualizerModel:
        return await self.create_or_update_equalizer(
            id=id,
            scope=channel.id,
            author=author,
            name=name,
            description=description,
            band_25=band_25,
            band_40=band_40,
            band_63=band_63,
            band_100=band_100,
            band_160=band_160,
            band_250=band_250,
            band_400=band_400,
            band_630=band_630,
            band_1000=band_1000,
            band_1600=band_1600,
            band_2500=band_2500,
            band_4000=band_4000,
            band_6300=band_6300,
            band_10000=band_10000,
            band_16000=band_16000,
        )

    async def create_or_update_guild_equalizer(
        self,
        guild: discord.Guild,
        id: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float = 0.0,
        band_40: float = 0.0,
        band_63: float = 0.0,
        band_100: float = 0.0,
        band_160: float = 0.0,
        band_250: float = 0.0,
        band_400: float = 0.0,
        band_630: float = 0.0,
        band_1000: float = 0.0,
        band_1600: float = 0.0,
        band_2500: float = 0.0,
        band_4000: float = 0.0,
        band_6300: float = 0.0,
        band_10000: float = 0.0,
        band_16000: float = 0.0,
    ) -> EqualizerModel:
        return await self.create_or_update_equalizer(
            id=id,
            scope=guild.id,
            author=author,
            name=name,
            description=description,
            band_25=band_25,
            band_40=band_40,
            band_63=band_63,
            band_100=band_100,
            band_160=band_160,
            band_250=band_250,
            band_400=band_400,
            band_630=band_630,
            band_1000=band_1000,
            band_1600=band_1600,
            band_2500=band_2500,
            band_4000=band_4000,
            band_6300=band_6300,
            band_10000=band_10000,
            band_16000=band_16000,
        )

    async def create_or_update_vc_equalizer(
        self,
        vc: discord.channel.VocalGuildChannel,
        id: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float = 0.0,
        band_40: float = 0.0,
        band_63: float = 0.0,
        band_100: float = 0.0,
        band_160: float = 0.0,
        band_250: float = 0.0,
        band_400: float = 0.0,
        band_630: float = 0.0,
        band_1000: float = 0.0,
        band_1600: float = 0.0,
        band_2500: float = 0.0,
        band_4000: float = 0.0,
        band_6300: float = 0.0,
        band_10000: float = 0.0,
        band_16000: float = 0.0,
    ) -> EqualizerModel:
        return await self.create_or_update_equalizer(
            id=id,
            scope=vc.id,
            author=author,
            name=name,
            description=description,
            band_25=band_25,
            band_40=band_40,
            band_63=band_63,
            band_100=band_100,
            band_160=band_160,
            band_250=band_250,
            band_400=band_400,
            band_630=band_630,
            band_1000=band_1000,
            band_1600=band_1600,
            band_2500=band_2500,
            band_4000=band_4000,
            band_6300=band_6300,
            band_10000=band_10000,
            band_16000=band_16000,
        )

    async def get_all_for_user(
        self,
        requester: int,
        *,
        vc: discord.channel.VocalGuildChannel = None,
        guild: discord.Guild = None,
        channel: discord.abc.MessageableChannel = None,
    ) -> tuple[
        list[EqualizerModel], list[EqualizerModel], list[EqualizerModel], list[EqualizerModel], list[EqualizerModel]
    ]:
        """
        Gets all equalizers a user has access to in a given context.

        Globals, User specific, Guild specific, Channel specific, VC specific.

        """
        global_equalizers = [p async for p in self.get_all_equalizers_by_scope(scope=self._client.bot.user.id)]
        user_equalizers = [p async for p in self.get_all_equalizers_by_scope(scope=requester)]
        vc_equalizers = []
        guild_equalizers = []
        channel_equalizers = []
        if vc is not None:
            vc_equalizers = [p async for p in self.get_all_equalizers_by_scope(scope=vc.id)]
        if guild is not None:
            guild_equalizers = [p async for p in self.get_all_equalizers_by_scope(scope=guild.id)]
        if channel is not None:
            channel_equalizers = [p async for p in self.get_all_equalizers_by_scope(scope=channel.id)]
        return global_equalizers, user_equalizers, guild_equalizers, channel_equalizers, vc_equalizers

    async def get_manageable_equalizers(
        self, requester: discord.abc.User, bot: BotT, *, name_or_id: str | None = None
    ) -> list[EqualizerModel]:
        if name_or_id:
            try:
                equalizers = await self.get_equalizer_by_name_or_id(name_or_id)
            except EntryNotFoundError:
                equalizers = []
        else:
            try:
                equalizers = [p async for p in self.get_all_equalizers()]
            except EntryNotFoundError:
                equalizers = []
        returning_list = []
        if equalizers:
            async for equalizer in AsyncIter(equalizers):
                if await equalizer.can_manage(requester=requester, bot=bot):
                    returning_list.append(equalizer)
        return returning_list

    @staticmethod
    async def count() -> int:
        """Returns the number of equalizers in the database."""
        return await pylav.sql.tables.equalizers.EqualizerRow.count()
