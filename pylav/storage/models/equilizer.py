from __future__ import annotations

import gzip
import io
import sys
from collections.abc import Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import aiohttp
import brotli  # type: ignore
import discord
import yaml
from piccolo.columns import Float

from pylav.compat import json
from pylav.constants.config import BROTLI_ENABLED
from pylav.constants.playlists import BUNDLED_PLAYLIST_IDS
from pylav.core.context import PyLavContext
from pylav.exceptions.playlist import InvalidPlaylistException
from pylav.logging import getLogger
from pylav.players import filters
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.equalizer import EqualizerRow
from pylav.type_hints.bot import DISCORD_BOT_TYPE

LOGGER = getLogger("PyLav.Database.Equalizer")


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True)
class Equalizer(CachedModel):
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

    def get_cache_key(self) -> str:
        return f"{self.scope}:{self.id}:{self.author}"

    async def save(self) -> Equalizer:
        """Save the Equalizer to the database.

        Returns
        -------
        Equalizer
            The Equalizer.
        """

        values = {
            EqualizerRow.scope: self.scope,
            EqualizerRow.author: self.author,
            EqualizerRow.name: self.name,
            EqualizerRow.description: self.description,
        }
        values |= self._get_save_defaults()

        eq = (
            await EqualizerRow.objects()
            .output(load_json=True)
            .get_or_create(EqualizerRow.id == self.id, defaults=values)
        )
        # noinspection PyProtectedMember
        if not eq._was_created:
            await EqualizerRow.update(values).where(EqualizerRow.id == self.id)
        return Equalizer(**eq.to_dict())

    @classmethod
    async def get(cls, identifier: int) -> Equalizer | None:
        """Get an equalizer from the database.

        Parameters
        ----------
        identifier: int
            The id of the equalizer.

        Returns
        -------
        Equalizer | None
            The equalizer if found, else None.
        """
        equalizer = (
            await EqualizerRow.select().where(EqualizerRow.id == identifier).first().output(load_json=True, nested=True)
        )
        return Equalizer(**equalizer) if equalizer else None

    async def delete(self) -> None:
        """Delete the equalizer from the database"""
        await EqualizerRow.delete().where(EqualizerRow.id == self.id)

    async def can_manage(self, bot: DISCORD_BOT_TYPE, requester: discord.abc.User) -> bool:  # noqa
        """Check if the requester can manage the equalizer.

        Parameters
        ----------
        bot: DISCORD_BOT_TYPE
            The bot.
        requester: discord.abc.User
            The requester.

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

    async def get_scope_name(self, bot: DISCORD_BOT_TYPE, mention: bool = True, guild: discord.Guild = None) -> str:
        """Get the name of the scope.

        Parameters
        ----------
        bot: DISCORD_BOT_TYPE
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

    async def get_author_name(self, bot: DISCORD_BOT_TYPE, mention: bool = True) -> str | None:
        """Get the name of the author.

        Parameters
        ----------
        bot: DISCORD_BOT_TYPE
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
            "bands": self._get_band_dict(),
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
                        with gzip.GzipFile(fileobj=cbio, mode="wb", compresslevel=9) as gzip_file:
                            yaml.safe_dump(data, gzip_file, default_flow_style=False, sort_keys=False, encoding="utf-8")
                    cbio.seek(0)
                    LOGGER.debug("SIZE COMPRESSED playlist [%s] (%s): %s", compression, self.name, sys.getsizeof(cbio))
                    yield cbio, compression
                    return
            yield bio, compression

    @classmethod
    async def from_yaml(cls, context: PyLavContext, scope: int, url: str) -> Equalizer:
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
        Equalizer
            The Equalizer.

        """
        try:
            async with aiohttp.ClientSession(auto_decompress=False, json_serialize=json.dumps) as session:
                async with session.get(url) as response:
                    data = await response.read()
                    if ".gz.pylav" in url:
                        data = gzip.decompress(data)
                    elif ".br.pylav" in url:
                        data = brotli.decompress(data)
                    data = yaml.safe_load(data)
        except Exception as e:
            raise InvalidPlaylistException(f"Invalid equalizer file - {e}") from e

        return cls(**cls._get_args(identifier=context.message.id, scope=scope, data=data))

    def to_dict(self) -> dict[str, int | str | float | dict[str, float]]:
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
            "bands": self._get_band_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Equalizer:
        """Deserialize a Equalizer from a dict.

        Parameters
        ----------
        data: dict
            The data to use to build the Equalizer

        Returns
        -------
        Equalizer
            The Equalizer
        """
        return cls(
            **cls._get_args(data=data),
        )

    def to_filter(self) -> filters.Equalizer:
        """Serialize the Equalizer to a Filter.

        Returns
        -------
        Equalizer
            The filter representation of the Equalizer
        """

        return filters.Equalizer(
            name=self.name or "CustomEqualizer",
            levels=self._get_band_list(),
        )

    @classmethod
    def from_filter(
        cls, equalizer: filters.Equalizer, context: PyLavContext, scope: int, description: str = None
    ) -> Equalizer:
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
        Equalizer
            The Equalizer built from the Equalizer object
        """
        return Equalizer(
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

    def _get_band_dict(self) -> dict[str, float]:
        bands = {}
        null_values = [None, 0.0]
        if self.band_25 not in null_values:
            bands["25"] = self.band_25
        if self.band_40 not in null_values:
            bands["40"] = self.band_40
        if self.band_63 not in null_values:
            bands["63"] = self.band_63
        if self.band_100 not in null_values:
            bands["100"] = self.band_100
        if self.band_160 not in null_values:
            bands["160"] = self.band_160
        if self.band_250 not in null_values:
            bands["250"] = self.band_250
        if self.band_400 not in null_values:
            bands["400"] = self.band_400
        if self.band_630 not in null_values:
            bands["630"] = self.band_630
        if self.band_1000 not in null_values:
            bands["1000"] = self.band_1000
        if self.band_1600 not in null_values:
            bands["1600"] = self.band_1600
        if self.band_2500 not in null_values:
            bands["2500"] = self.band_2500
        if self.band_4000 not in null_values:
            bands["4000"] = self.band_4000
        if self.band_6300 not in null_values:
            bands["6300"] = self.band_6300
        if self.band_10000 not in null_values:
            bands["10000"] = self.band_10000
        if self.band_16000 not in null_values:
            bands["16000"] = self.band_16000
        return bands

    def _get_save_defaults(self) -> dict[Float, float]:
        return {
            EqualizerRow.band_25: self.band_25 or None,
            EqualizerRow.band_40: self.band_40 or None,
            EqualizerRow.band_63: self.band_63 or None,
            EqualizerRow.band_100: self.band_100 or None,
            EqualizerRow.band_160: self.band_160 or None,
            EqualizerRow.band_250: self.band_250 or None,
            EqualizerRow.band_400: self.band_400 or None,
            EqualizerRow.band_630: self.band_630 or None,
            EqualizerRow.band_1000: self.band_1000 or None,
            EqualizerRow.band_1600: self.band_1600 or None,
            EqualizerRow.band_2500: self.band_2500 or None,
            EqualizerRow.band_4000: self.band_4000 or None,
            EqualizerRow.band_6300: self.band_6300 or None,
            EqualizerRow.band_10000: self.band_10000 or None,
            EqualizerRow.band_16000: self.band_16000 or None,
        }

    def _get_band_list(self) -> list[dict[str, float]]:
        levels = []
        null_values = [None, 0.0]
        if self.band_25 not in null_values:
            levels.append({"band": 0, "gain": self.band_25})
        if self.band_40 not in null_values:
            levels.append({"band": 1, "gain": self.band_40})
        if self.band_63 not in null_values:
            levels.append({"band": 2, "gain": self.band_63})
        if self.band_100 not in null_values:
            levels.append({"band": 3, "gain": self.band_100})
        if self.band_160 not in null_values:
            levels.append({"band": 4, "gain": self.band_160})
        if self.band_250 not in null_values:
            levels.append({"band": 5, "gain": self.band_250})
        if self.band_400 not in null_values:
            levels.append({"band": 6, "gain": self.band_400})
        if self.band_630 not in null_values:
            levels.append({"band": 7, "gain": self.band_630})
        if self.band_1000 not in null_values:
            levels.append({"band": 8, "gain": self.band_1000})
        if self.band_1600 not in null_values:
            levels.append({"band": 9, "gain": self.band_1600})
        if self.band_2500 not in null_values:
            levels.append({"band": 10, "gain": self.band_2500})
        if self.band_4000 not in null_values:
            levels.append({"band": 11, "gain": self.band_4000})
        if self.band_6300 not in null_values:
            levels.append({"band": 12, "gain": self.band_6300})
        if self.band_10000 not in null_values:
            levels.append({"band": 13, "gain": self.band_10000})
        if self.band_16000 not in null_values:
            levels.append({"band": 14, "gain": self.band_16000})
        return levels

    @staticmethod
    def _get_args(
        data: dict[str, dict[str, float]],
        identifier: int | None = None,
        scope: int | None = None,
        name: str | None = None,
        author: int | None = None,
        description: str | None = None,
    ) -> dict[str, int | str | float | None]:
        return dict(
            band_25=data["bands"]["25"] if "25" in data["bands"] else None,
            band_40=data["bands"]["40"] if "40" in data["bands"] else None,
            band_63=data["bands"]["63"] if "63" in data["bands"] else None,
            band_100=data["bands"]["100"] if "100" in data["bands"] else None,
            band_160=data["bands"]["160"] if "160" in data["bands"] else None,
            band_250=data["bands"]["250"] if "250" in data["bands"] else None,
            band_400=data["bands"]["400"] if "400" in data["bands"] else None,
            band_630=data["bands"]["630"] if "630" in data["bands"] else None,
            band_1000=data["bands"]["1000"] if "1000" in data["bands"] else None,
            band_1600=data["bands"]["1600"] if "1600" in data["bands"] else None,
            band_2500=data["bands"]["2500"] if "2500" in data["bands"] else None,
            band_4000=data["bands"]["4000"] if "4000" in data["bands"] else None,
            band_6300=data["bands"]["6300"] if "6300" in data["bands"] else None,
            band_10000=data["bands"]["10000"] if "10000" in data["bands"] else None,
            band_16000=data["bands"]["16000"] if "16000" in data["bands"] else None,
            id=identifier or data["id"],
            scope=scope or data["scope"],
            name=name or data["name"],
            author=author or data["author"],
            description=description or data["description"],
        )
