from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import discord

from pylav._logging import getLogger
from pylav.exceptions import EntryNotFoundError
from pylav.sql import tables
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
            equalizers = await tables.EqualizerRow.select().where(
                tables.EqualizerRow.name.ilike(f"%{equalizer_name.lower()}%")
            )
        else:
            equalizers = (
                await tables.EqualizerRow.select()
                .where(tables.EqualizerRow.name.ilike(f"%{equalizer_name.lower()}%"))
                .limit(limit)
            )

        if not equalizers:
            raise EntryNotFoundError(f"Equalizer with name {equalizer_name} not found")
        return [EqualizerModel(**equalizer) for equalizer in equalizers]

    @staticmethod
    async def get_equalizer_by_id(equalizer_id: int | str) -> EqualizerModel:
        try:
            equalizer_id = int(equalizer_id)
        except ValueError as e:
            raise EntryNotFoundError(f"Equalizer with id {equalizer_id} not found") from e
        equalizer = await tables.EqualizerRow.select().where(tables.EqualizerRow.id == equalizer_id).limit(1).first()
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
        equalizers = await tables.EqualizerRow.select().where(tables.EqualizerRow.author == author)
        if not equalizers:
            raise EntryNotFoundError(f"Equalizer with author {author} not found")
        return [EqualizerModel(**equalizer) for equalizer in equalizers]

    @staticmethod
    async def get_equalizers_by_scope(scope: int) -> list[EqualizerModel]:
        equalizers = await tables.EqualizerRow.select().where(tables.EqualizerRow.scope == scope)
        if not equalizers:
            raise EntryNotFoundError(f"Equalizer with scope {scope} not found")
        return [EqualizerModel(**equalizer) for equalizer in equalizers]

    @staticmethod
    async def get_all_equalizers() -> AsyncIterator[EqualizerModel]:
        for entry in await tables.EqualizerRow.select():
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
            tables.EqualizerRow.scope: scope,
            tables.EqualizerRow.author: author,
            tables.EqualizerRow.name: name,
            tables.EqualizerRow.description: description,
            tables.EqualizerRow.band_25: band_25,
            tables.EqualizerRow.band_40: band_40,
            tables.EqualizerRow.band_63: band_63,
            tables.EqualizerRow.band_100: band_100,
            tables.EqualizerRow.band_160: band_160,
            tables.EqualizerRow.band_250: band_250,
            tables.EqualizerRow.band_400: band_400,
            tables.EqualizerRow.band_630: band_630,
            tables.EqualizerRow.band_1000: band_1000,
            tables.EqualizerRow.band_1600: band_1600,
            tables.EqualizerRow.band_2500: band_2500,
            tables.EqualizerRow.band_4000: band_4000,
            tables.EqualizerRow.band_6300: band_6300,
            tables.EqualizerRow.band_10000: band_10000,
            tables.EqualizerRow.band_16000: band_16000,
        }
        equalizer = (
            await tables.EqualizerRow.objects()
            .output(load_json=True)
            .get_or_create(tables.EqualizerRow.id == id, defaults=values)
        )
        if not equalizer._was_created:
            await tables.EqualizerRow.update(values).where(tables.EqualizerRow.id == id)
        return EqualizerModel(**equalizer.to_dict())

    @staticmethod
    async def delete_equalizer(equalizer_id: int) -> None:
        await tables.EqualizerRow.delete().where(tables.EqualizerRow.id == equalizer_id)

    @staticmethod
    async def get_all_equalizers_by_author(author: int) -> AsyncIterator[EqualizerModel]:
        for entry in await tables.EqualizerRow.select().where(tables.EqualizerRow.author == author):
            yield EqualizerModel(**entry)

    @staticmethod
    async def get_all_equalizers_by_scope(scope: int) -> AsyncIterator[EqualizerModel]:
        for entry in await tables.EqualizerRow.select().where(tables.EqualizerRow.scope == scope):
            yield EqualizerModel(**entry)

    @staticmethod
    async def get_all_equalizers_by_scope_and_author(scope: int, author: int) -> AsyncIterator[EqualizerModel]:
        for entry in await tables.EqualizerRow.select().where(
            tables.EqualizerRow.scope == scope, tables.EqualizerRow.author == author
        ):
            yield EqualizerModel(**entry)

    async def get_global_equalizers(self) -> AsyncIterator[EqualizerModel]:
        for entry in await tables.EqualizerRow.select().where(tables.EqualizerRow.scope == self._client.bot.user.id):  # type: ignore
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
        return await tables.EqualizerRow.count()
