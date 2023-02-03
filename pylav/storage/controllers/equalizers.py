from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import discord
from piccolo.columns import Float

from pylav.exceptions.database import EntryNotFoundException
from pylav.logging import getLogger
from pylav.storage.database.tables.equalizer import EqualizerRow
from pylav.storage.models import equilizer
from pylav.type_hints.bot import DISCORD_BOT_TYPE

LOGGER = getLogger("PyLav.Database.Controller.Equalizer")

if TYPE_CHECKING:
    from pylav.core.client import Client


class EqualizerController:
    __slots__ = ("_client",)

    def __init__(self, client: Client) -> None:
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    async def get_equalizer_by_name(equalizer_name: str, limit: int = None) -> list[equilizer.Equalizer]:
        if limit is None:
            equalizers = (
                await EqualizerRow.select()
                .where(EqualizerRow.name.ilike(f"%{equalizer_name.lower()}%"))
                .output(load_json=True, nested=True)
            )
        else:
            equalizers = (
                await EqualizerRow.select().where(EqualizerRow.name.ilike(f"%{equalizer_name.lower()}%")).limit(limit)
            ).output(load_json=True, nested=True)

        if not equalizers:
            raise EntryNotFoundException(f"Equalizer with name {equalizer_name} not found")
        return [equilizer.Equalizer(**equalizer) for equalizer in equalizers]

    @staticmethod
    async def get_equalizer_by_id(identifier: int | str) -> equilizer.Equalizer:
        try:
            identifier = int(identifier)
        except ValueError as e:
            raise EntryNotFoundException(f"Equalizer with id {identifier} not found") from e
        equalizer = (
            await EqualizerRow.select().where(EqualizerRow.id == identifier).first().output(load_json=True, nested=True)
        )
        if not equalizer:
            raise EntryNotFoundException(f"Equalizer with ID {identifier} not found")
        return equilizer.Equalizer(**equalizer)

    async def get_equalizer_by_name_or_id(
        self, equalizer_name_or_id: int | str, limit: int = None
    ) -> list[equilizer.Equalizer]:
        try:
            return [await self.get_equalizer_by_id(equalizer_name_or_id)]
        except EntryNotFoundException:
            return await self.get_equalizer_by_name(equalizer_name_or_id, limit=limit)

    @staticmethod
    async def get_equalizers_by_author(author: int) -> list[equilizer.Equalizer]:
        equalizers = (
            await EqualizerRow.select().where(EqualizerRow.author == author).output(load_json=True, nested=True)
        )
        if not equalizers:
            raise EntryNotFoundException(f"Equalizer with author {author} not found")
        return [equilizer.Equalizer(**equalizer) for equalizer in equalizers]

    @staticmethod
    async def get_equalizers_by_scope(scope: int) -> list[equilizer.Equalizer]:
        equalizers = await EqualizerRow.select().where(EqualizerRow.scope == scope).output(load_json=True, nested=True)
        if not equalizers:
            raise EntryNotFoundException(f"Equalizer with scope {scope} not found")
        return [equilizer.Equalizer(**equalizer) for equalizer in equalizers]

    @staticmethod
    async def get_all_equalizers() -> AsyncIterator[equilizer.Equalizer]:
        for entry in await EqualizerRow.select().output(load_json=True, nested=True):
            yield equilizer.Equalizer(**entry)

    @staticmethod
    def _get_equalizer_band_defaults(*args: tuple[Float, float | None]) -> dict[Float, float]:
        null_values = {None, 0.0}
        return {band: value for band, value in args if value not in null_values}

    @staticmethod
    async def create_or_update_equalizer(
        identifier: int,
        scope: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float | None = None,
        band_40: float | None = None,
        band_63: float | None = None,
        band_100: float | None = None,
        band_160: float | None = None,
        band_250: float | None = None,
        band_400: float | None = None,
        band_630: float | None = None,
        band_1000: float | None = None,
        band_1600: float | None = None,
        band_2500: float | None = None,
        band_4000: float | None = None,
        band_6300: float | None = None,
        band_10000: float | None = None,
        band_16000: float | None = None,
    ) -> equilizer.Equalizer:
        values = {
            EqualizerRow.scope: scope,
            EqualizerRow.author: author,
            EqualizerRow.name: name,
            EqualizerRow.description: description,
        }
        values |= EqualizerController._get_equalizer_band_defaults(
            (EqualizerRow.band_25, band_25),
            (EqualizerRow.band_40, band_40),
            (EqualizerRow.band_63, band_63),
            (EqualizerRow.band_100, band_100),
            (EqualizerRow.band_160, band_160),
            (EqualizerRow.band_250, band_250),
            (EqualizerRow.band_400, band_400),
            (EqualizerRow.band_630, band_630),
            (EqualizerRow.band_1000, band_1000),
            (EqualizerRow.band_1600, band_1600),
            (EqualizerRow.band_2500, band_2500),
            (EqualizerRow.band_4000, band_4000),
            (EqualizerRow.band_6300, band_6300),
            (EqualizerRow.band_10000, band_10000),
            (EqualizerRow.band_16000, band_16000),
        )
        equalizer = (
            await EqualizerRow.objects()
            .output(load_json=True)
            .get_or_create(EqualizerRow.id == identifier, defaults=values)
        )
        # noinspection PyProtectedMember
        if not equalizer._was_created:
            await EqualizerRow.update(values).where(EqualizerRow.id == identifier)
        return equilizer.Equalizer(**equalizer.to_dict())

    @staticmethod
    async def delete_equalizer(equalizer_id: int) -> None:
        await EqualizerRow.delete().where(EqualizerRow.id == equalizer_id)

    @staticmethod
    async def get_all_equalizers_by_author(author: int) -> AsyncIterator[equilizer.Equalizer]:
        for entry in (
            await EqualizerRow.select().where(EqualizerRow.author == author).output(load_json=True, nested=True)
        ):
            yield equilizer.Equalizer(**entry)

    @staticmethod
    async def get_all_equalizers_by_scope(scope: int) -> AsyncIterator[equilizer.Equalizer]:
        for entry in await EqualizerRow.select().where(EqualizerRow.scope == scope).output(load_json=True, nested=True):
            yield equilizer.Equalizer(**entry)

    @staticmethod
    async def get_all_equalizers_by_scope_and_author(scope: int, author: int) -> AsyncIterator[equilizer.Equalizer]:
        for entry in (
            await EqualizerRow.select()
            .where(
                EqualizerRow.scope == scope,
                EqualizerRow.author == author,
            )
            .output(load_json=True, nested=True)
        ):
            yield equilizer.Equalizer(**entry)

    async def get_global_equalizers(self) -> AsyncIterator[equilizer.Equalizer]:
        for entry in (
            await EqualizerRow.select()
            .where(EqualizerRow.scope == self._client.bot.user.id)  # type: ignore
            .output(load_json=True, nested=True)
        ):
            yield equilizer.Equalizer(**entry)

    async def create_or_update_global_equalizer(
        self,
        identifier: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float | None = None,
        band_40: float | None = None,
        band_63: float | None = None,
        band_100: float | None = None,
        band_160: float | None = None,
        band_250: float | None = None,
        band_400: float | None = None,
        band_630: float | None = None,
        band_1000: float | None = None,
        band_1600: float | None = None,
        band_2500: float | None = None,
        band_4000: float | None = None,
        band_6300: float | None = None,
        band_10000: float | None = None,
        band_16000: float | None = None,
    ) -> equilizer.Equalizer:
        return await self.create_or_update_equalizer(
            identifier=identifier,
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
        user_id: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float | None = None,
        band_40: float | None = None,
        band_63: float | None = None,
        band_100: float | None = None,
        band_160: float | None = None,
        band_250: float | None = None,
        band_400: float | None = None,
        band_630: float | None = None,
        band_1000: float | None = None,
        band_1600: float | None = None,
        band_2500: float | None = None,
        band_4000: float | None = None,
        band_6300: float | None = None,
        band_10000: float | None = None,
        band_16000: float | None = None,
    ) -> equilizer.Equalizer:
        return await self.create_or_update_equalizer(
            identifier=user_id,
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
        text_channel: discord.abc.MessageableChannel,
        identifier: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float | None = None,
        band_40: float | None = None,
        band_63: float | None = None,
        band_100: float | None = None,
        band_160: float | None = None,
        band_250: float | None = None,
        band_400: float | None = None,
        band_630: float | None = None,
        band_1000: float | None = None,
        band_1600: float | None = None,
        band_2500: float | None = None,
        band_4000: float | None = None,
        band_6300: float | None = None,
        band_10000: float | None = None,
        band_16000: float | None = None,
    ) -> equilizer.Equalizer:
        return await self.create_or_update_equalizer(
            identifier=identifier,
            scope=text_channel.id,
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
        identifier: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float | None = None,
        band_40: float | None = None,
        band_63: float | None = None,
        band_100: float | None = None,
        band_160: float | None = None,
        band_250: float | None = None,
        band_400: float | None = None,
        band_630: float | None = None,
        band_1000: float | None = None,
        band_1600: float | None = None,
        band_2500: float | None = None,
        band_4000: float | None = None,
        band_6300: float | None = None,
        band_10000: float | None = None,
        band_16000: float | None = None,
    ) -> equilizer.Equalizer:
        return await self.create_or_update_equalizer(
            identifier=identifier,
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
        voice_channel: discord.channel.VocalGuildChannel,
        identifier: int,
        author: int,
        name: str,
        description: str | None = None,
        band_25: float | None = None,
        band_40: float | None = None,
        band_63: float | None = None,
        band_100: float | None = None,
        band_160: float | None = None,
        band_250: float | None = None,
        band_400: float | None = None,
        band_630: float | None = None,
        band_1000: float | None = None,
        band_1600: float | None = None,
        band_2500: float | None = None,
        band_4000: float | None = None,
        band_6300: float | None = None,
        band_10000: float | None = None,
        band_16000: float | None = None,
    ) -> equilizer.Equalizer:
        return await self.create_or_update_equalizer(
            identifier=identifier,
            scope=voice_channel.id,
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
        voice_channel: discord.channel.VocalGuildChannel = None,
        guild: discord.Guild = None,
        channel: discord.abc.MessageableChannel = None,
    ) -> tuple[
        list[equilizer.Equalizer],
        list[equilizer.Equalizer],
        list[equilizer.Equalizer],
        list[equilizer.Equalizer],
        list[equilizer.Equalizer],
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
        if voice_channel is not None:
            vc_equalizers = [p async for p in self.get_all_equalizers_by_scope(scope=voice_channel.id)]
        if guild is not None:
            guild_equalizers = [p async for p in self.get_all_equalizers_by_scope(scope=guild.id)]
        if channel is not None:
            channel_equalizers = [p async for p in self.get_all_equalizers_by_scope(scope=channel.id)]
        return global_equalizers, user_equalizers, guild_equalizers, channel_equalizers, vc_equalizers

    async def get_manageable_equalizers(
        self, requester: discord.abc.User, bot: DISCORD_BOT_TYPE, *, name_or_id: str | None = None
    ) -> list[equilizer.Equalizer]:
        if name_or_id:
            try:
                equalizers = await self.get_equalizer_by_name_or_id(name_or_id)
            except EntryNotFoundException:
                equalizers = []
        else:
            try:
                equalizers = [p async for p in self.get_all_equalizers()]
            except EntryNotFoundException:
                equalizers = []
        returning_list = []
        if equalizers:
            for equalizer in equalizers:
                if await equalizer.can_manage(requester=requester, bot=bot):
                    returning_list.append(equalizer)
        return returning_list

    @staticmethod
    async def count() -> int:
        """Returns the number of equalizers in the database."""
        return await EqualizerRow.count()
