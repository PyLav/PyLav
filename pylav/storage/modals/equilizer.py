from __future__ import annotations

import gzip
import io
import sys
from collections.abc import Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import aiohttp
import brotli
import discord
import ujson
import yaml

from pylav.constants.config import BROTLI_ENABLED
from pylav.constants.playlists import BUNDLED_PLAYLIST_IDS
from pylav.exceptions.playlist import InvalidPlaylistException
from pylav.logging import getLogger
from pylav.players.filters import Equalizer
from pylav.storage.database.tables.equalizer import EqualizerRow

LOGGER = getLogger("PyLav.Database.Equalizer")


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class EqualizerModel:
    id: int
    scope: int
    author: int
    name: str | None = None
    description: str | None = None
    band_25: float | None = None
    band_40: float | None = None
    band_63: float | None = None
    band_100: float | None = None
    band_160: float | None = None
    band_250: float | None = None
    band_400: float | None = None
    band_630: float | None = None
    band_1000: float | None = None
    band_1600: float | None = None
    band_2500: float | None = None
    band_4000: float | None = None
    band_6300: float | None = None
    band_10000: float | None = None
    band_16000: float | None = None

    async def save(self) -> EqualizerModel:
        """Save the Equalizer to the database.

        Returns
        -------
        EqualizerModel
            The Equalizer.
        """

        values = {
            EqualizerRow.scope: self.scope,
            EqualizerRow.author: self.author,
            EqualizerRow.name: self.name,
            EqualizerRow.description: self.description,
            EqualizerRow.band_25: self.band_25,
            EqualizerRow.band_40: self.band_40,
            EqualizerRow.band_63: self.band_63,
            EqualizerRow.band_100: self.band_100,
            EqualizerRow.band_160: self.band_160,
            EqualizerRow.band_250: self.band_250,
            EqualizerRow.band_400: self.band_400,
            EqualizerRow.band_630: self.band_630,
            EqualizerRow.band_1000: self.band_1000,
            EqualizerRow.band_1600: self.band_1600,
            EqualizerRow.band_2500: self.band_2500,
            EqualizerRow.band_4000: self.band_4000,
            EqualizerRow.band_6300: self.band_6300,
            EqualizerRow.band_10000: self.band_10000,
            EqualizerRow.band_16000: self.band_16000,
        }
        eq = (
            await EqualizerRow.objects()
            .output(load_json=True)
            .get_or_create(EqualizerRow.id == self.id, defaults=values)
        )
        if not eq._was_created:
            await EqualizerRow.update(values).where(EqualizerRow.id == self.id)
        return EqualizerModel(**eq.to_dict())

    @classmethod
    async def get(cls, identifier: int) -> EqualizerModel | None:
        """Get an equalizer from the database.

        Parameters
        ----------
        identifier: int
            The id of the equalizer.

        Returns
        -------
        EqualizerModel | None
            The equalizer if found, else None.
        """
        equalizer = (
            await EqualizerRow.select().where(EqualizerRow.id == identifier).first().output(load_json=True, nested=True)
        )
        return EqualizerModel(**equalizer) if equalizer else None

    async def delete(self):
        """Delete the equalizer from the database"""
        await EqualizerRow.delete().where(EqualizerRow.id == self.id)

    async def can_manage(self, bot: BotType, requester: discord.abc.User, guild: discord.Guild = None) -> bool:  # noqa
        """Check if the requester can manage the equalizer.

        Parameters
        ----------
        bot: BotType
            The bot.
        requester: discord.abc.User
            The requester.
        guild: discord.Guild | None
            The guild.

        Returns
        -------
        bool
            If the requester can manage the equalizer.
        """
        if self.scope in BUNDLED_PLAYLIST_IDS:
            return False
        if requester.id in ((ids := getattr(bot, "owner_ids")) or ()) or requester.id == bot.owner_id:  # noqa
            return True
        elif self.scope == bot.user.id:
            return False
        return self.author == requester.id

    async def get_scope_name(self, bot: BotType, mention: bool = True, guild: discord.Guild = None) -> str:
        """Get the name of the scope.

        Parameters
        ----------
        bot: BotType
            The bot.
        mention: bool
            If the name should be mentionable.
        guild: discord.Guild | None
            The guild.

        Returns
        -------
        str
            The name of the scope.
        """
        if bot.user.id == self.scope:
            return f"(Global) {bot.user.mention}" if mention else f"(Global) {bot.user}"
        elif guild_ := bot.get_guild(self.scope):
            if guild_:
                guild = guild_
            return f"(Server) {guild.name}"
        elif guild and (channel := guild.get_channel_or_thread(self.scope)):
            return f"(Channel) {channel.mention}" if mention else f"(Channel) {channel.name}"

        elif (
            (guild := guild_ or guild)
            and (guild and (author := guild.get_member(self.scope)))  # noqa
            or (author := bot.get_user(self.author))
        ):
            return f"(User) {author.mention}" if mention else f"(User) {author}"
        else:
            return f"(Invalid) {self.scope}"

    async def get_author_name(self, bot: BotType, mention: bool = True) -> str | None:
        """Get the name of the author.

        Parameters
        ----------
        bot: BotType
            The bot.
        mention: bool
            If the name should be mentionable.

        Returns
        -------
        str | None
            The name of the author.
        """
        if user := bot.get_user(self.author):
            return f"{user.mention}" if mention else f"{user}"
        return f"{self.author}"

    @asynccontextmanager
    async def to_yaml(self, guild: discord.Guild) -> Iterator[tuple[io.BytesIO, str | None]]:
        """Serialize the Equalizer to a YAML file.

        yields a tuple of (io.BytesIO, bool) where the bool is whether the playlist file was compressed using Gzip

        Parameters
        ----------
        guild: discord.Guild
            The guild.

        Yields
        -------
        tuple[io.BytesIO, str | None]
            The YAML file and the compression type.

        """
        data = {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "description": self.description,
            "scope": self.scope,
            "bands": {
                "25": self.band_25,
                "40": self.band_40,
                "63": self.band_63,
                "100": self.band_100,
                "160": self.band_160,
                "250": self.band_250,
                "400": self.band_400,
                "630": self.band_630,
                "1000": self.band_1000,
                "1600": self.band_1600,
                "2500": self.band_2500,
                "4000": self.band_4000,
                "6300": self.band_6300,
                "10000": self.band_10000,
                "16000": self.band_16000,
            },
        }
        compression = None
        with io.BytesIO() as bio:
            yaml.safe_dump(data, bio, default_flow_style=False, sort_keys=False, encoding="utf-8")
            bio.seek(0)
            LOGGER.debug("SIZE UNCOMPRESSED playlist (%s): %s", self.name, sys.getsizeof(bio))
            if sys.getsizeof(bio) > guild.filesize_limit:
                with io.BytesIO() as cbio:
                    if BROTLI_ENABLED:
                        compression = "brotli"
                        cbio.write(brotli.compress(yaml.dump(data, encoding="utf-8")))
                    else:
                        compression = "gzip"
                        with gzip.GzipFile(fileobj=cbio, mode="wb", compresslevel=9) as gfile:
                            yaml.safe_dump(data, gfile, default_flow_style=False, sort_keys=False, encoding="utf-8")
                    cbio.seek(0)
                    LOGGER.debug("SIZE COMPRESSED playlist [%s] (%s): %s", compression, self.name, sys.getsizeof(cbio))
                    yield cbio, compression
                    return
            yield bio, compression

    @classmethod
    async def from_yaml(cls, context: PyLavContext, scope: int, url: str) -> EqualizerModel:
        """Deserialize a Equalizer from a YAML file.

        Parameters
        ----------
        context: PyLavContext
            The context.
        scope: int
            The scope.
        url: str
            The URL to the YAML file.

        Returns
        -------
        EqualizerModel
            The Equalizer.

        """
        try:
            async with aiohttp.ClientSession(auto_decompress=False, json_serialize=ujson.dumps) as session:
                async with session.get(url) as response:
                    data = await response.read()
                    if ".gz.pylav" in url:
                        data = gzip.decompress(data)
                    elif ".br.pylav" in url:
                        data = brotli.decompress(data)
                    data = yaml.safe_load(data)
        except Exception as e:
            raise InvalidPlaylistException(f"Invalid equalizer file - {e}") from e
        return cls(
            id=context.message.id,
            scope=scope,
            name=data["name"],
            author=data["author"],
            description=data["description"],
            band_25=data["bands"]["25"],
            band_40=data["bands"]["40"],
            band_63=data["bands"]["63"],
            band_100=data["bands"]["100"],
            band_160=data["bands"]["160"],
            band_250=data["bands"]["250"],
            band_400=data["bands"]["400"],
            band_630=data["bands"]["630"],
            band_1000=data["bands"]["1000"],
            band_1600=data["bands"]["1600"],
            band_2500=data["bands"]["2500"],
            band_4000=data["bands"]["4000"],
            band_6300=data["bands"]["6300"],
            band_10000=data["bands"]["10000"],
            band_16000=data["bands"]["16000"],
        )

    def to_dict(self) -> dict:
        """Serialize the Equalizer to a dict.

        Returns
        -------
        dict
            The dict representation of the Equalizer.
        """

        return {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "description": self.description,
            "scope": self.scope,
            "bands": {
                "25": self.band_25,
                "40": self.band_40,
                "63": self.band_63,
                "100": self.band_100,
                "160": self.band_160,
                "250": self.band_250,
                "400": self.band_400,
                "630": self.band_630,
                "1000": self.band_1000,
                "1600": self.band_1600,
                "2500": self.band_2500,
                "4000": self.band_4000,
                "6300": self.band_6300,
                "10000": self.band_10000,
                "16000": self.band_16000,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> EqualizerModel:
        """Deserialize a Equalizer from a dict.

        Parameters
        ----------
        data: dict
            The data to use to build the Equalizer

        Returns
        -------
        EqualizerModel
            The Equalizer
        """
        return cls(
            id=data["id"],
            scope=data["scope"],
            name=data["name"],
            author=data["author"],
            description=data["description"],
            band_25=data["bands"]["25"],
            band_40=data["bands"]["40"],
            band_63=data["bands"]["63"],
            band_100=data["bands"]["100"],
            band_160=data["bands"]["160"],
            band_250=data["bands"]["250"],
            band_400=data["bands"]["400"],
            band_630=data["bands"]["630"],
            band_1000=data["bands"]["1000"],
            band_1600=data["bands"]["1600"],
            band_2500=data["bands"]["2500"],
            band_4000=data["bands"]["4000"],
            band_6300=data["bands"]["6300"],
            band_10000=data["bands"]["10000"],
            band_16000=data["bands"]["16000"],
        )

    def to_filter(self) -> Equalizer:
        """Serialize the Equalizer to a Filter.

        Returns
        -------
        Equalizer
            The filter representation of the Equalizer
        """
        return Equalizer(
            name=self.name or "CustomEqualizer",
            levels=[
                {"band": 0, "gain": self.band_25},
                {"band": 1, "gain": self.band_40},
                {"band": 2, "gain": self.band_63},
                {"band": 3, "gain": self.band_100},
                {"band": 4, "gain": self.band_160},
                {"band": 5, "gain": self.band_250},
                {"band": 6, "gain": self.band_400},
                {"band": 7, "gain": self.band_630},
                {"band": 8, "gain": self.band_1000},
                {"band": 9, "gain": self.band_1600},
                {"band": 10, "gain": self.band_2500},
                {"band": 11, "gain": self.band_4000},
                {"band": 12, "gain": self.band_6300},
                {"band": 13, "gain": self.band_10000},
                {"band": 14, "gain": self.band_16000},
            ],
        )

    @classmethod
    def from_filter(
        cls, equalizer: Equalizer, context: PyLavContext, scope: int, description: str = None
    ) -> EqualizerModel:
        """Deserialize a Equalizer from a Filter.

        Parameters
        ----------
        equalizer: Equalizer
            The filter object
        context: PyLavContext
            The Context
        scope: int
            The scope number
        description: str
            The description of the Equalizer

        Returns
        -------
        EqualizerModel
            The EqualizerModel built from the Equalizer object
        """
        return EqualizerModel(
            id=context.message.id,
            scope=scope,
            name=equalizer.name,
            author=context.author.id,
            description=description,
            band_25=equalizer.index[0],
            band_40=equalizer.index[1],
            band_63=equalizer.index[2],
            band_100=equalizer.index[3],
            band_160=equalizer.index[4],
            band_250=equalizer.index[5],
            band_400=equalizer.index[6],
            band_630=equalizer.index[7],
            band_1000=equalizer.index[8],
            band_1600=equalizer.index[9],
            band_2500=equalizer.index[10],
            band_4000=equalizer.index[11],
            band_6300=equalizer.index[12],
            band_10000=equalizer.index[13],
            band_16000=equalizer.index[14],
        )
