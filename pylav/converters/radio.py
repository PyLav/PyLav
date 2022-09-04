from __future__ import annotations

import asyncio
from operator import attrgetter
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

import asyncstdlib
from asyncstdlib import heapq
from discord.app_commands import Choice, Transformer
from discord.ext import commands
from rapidfuzz import fuzz

from pylav import getLogger
from pylav.types import ContextT, InteractionT
from pylav.utils import shorten_string

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLavPlayer", Path(__file__))
except ImportError:
    _ = lambda x: x

LOGGER = getLogger("red.3pt.PyLav-Shared.converters.radio")

if TYPE_CHECKING:
    from pylav.radio.objects import Codec, Country, CountryCode, Language, State, Station, Tag

    StationConverter = TypeVar("StationConverter", bound="list[Station]")
    TagConverter = TypeVar("TagConverter", bound=list[Tag])
    LanguageConverter = TypeVar("LanguageConverter", bound=list[Language])
    StateConverter = TypeVar("StateConverter", bound=list[State])
    CodecConverter = TypeVar("CodecConverter", bound=list[Codec])
    CountryCodeConverter = TypeVar("CountryCodeConverter", bound=list[CountryCode])
    CountryConverter = TypeVar("CountryConverter", bound=list[Country])
else:

    class StationConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[Station]:
            """Converts a station name to a matching object"""
            from pylav import EntryNotFoundError

            try:
                station = await ctx.lavalink.radio_browser.station_by_uuid(arg)
                if station:
                    return station
                stations = await ctx.lavalink.radio_browser.stations()
            except EntryNotFoundError as e:
                raise commands.BadArgument(_("Station with name `{arg}` not found").format(arg=arg)) from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), stations)):
                return await asyncstdlib.sorted(r, key=attrgetter("lastcheckoktime_iso8601"), reverse=True)
            raise commands.BadArgument(_("Station with name `{arg}` not found").format(arg=arg))

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[Station]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            data = interaction.data
            options = data.get("options", [])
            kwargs = {"order": "lastcheckok"}
            if options:
                country_code = [v for v in options if v.get("name") == "countrycode"]
                country = [v for v in options if v.get("name") == "country"]
                state = [v for v in options if v.get("name") == "state"]
                language = [v for v in options if v.get("name") == "language"]
                tags = [v for v in options if v.get("name", "").startswith("tag")]
                if country_code and (val := country_code[0].get("value")):
                    kwargs["countrycode"] = val
                if country and (val := country[0].get("value")):
                    kwargs["country"] = val
                    kwargs["country_exact"] = any(
                        True
                        for t in await interaction.client.lavalink.radio_browser.countries(
                            code=kwargs.get("countrycode")
                        )
                        if t.name == val
                    )
                if state and (val := state[0].get("value")):
                    kwargs["state"] = val
                    kwargs["state_exact"] = any(
                        True
                        for t in await interaction.client.lavalink.radio_browser.states(
                            country=kwargs["country"] if kwargs.get("country_exact") else None
                        )
                        if t.name == val
                    )
                if language and (val := language[0].get("value")):
                    kwargs["language"] = val
                    kwargs["language_exact"] = any(
                        True for t in await interaction.client.lavalink.radio_browser.languages() if t.name == val
                    )
                if tags:
                    if len(tags) == 1 and (val := tags[0].get("value")):
                        kwargs["tag"] = val
                        kwargs["tag_exact"] = any(
                            True for t in await interaction.client.lavalink.radio_browser.tags() if t.name == val
                        )
                    elif len(tags) > 1:
                        kwargs["tag_list"] = ",".join([tv for t in tags if (tv := t.get("value"))])

            if current:
                kwargs["name"] = current
            stations = await interaction.client.lavalink.radio_browser.search(limit=25, **kwargs)
            if not current:
                return [
                    Choice(
                        name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"),
                        value=f"{e.stationuuid}",
                    )
                    for e in stations
                ]

            async def _filter(c):
                return await asyncio.to_thread(fuzz.token_set_ratio, current, c.name)

            extracted: list[Station] = await heapq.nlargest(asyncstdlib.iter(stations), n=25, key=_filter)

            return [
                Choice(
                    name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.stationuuid}"
                )
                for e in extracted
            ]

    class TagConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[Tag]:
            """Converts a Tag name to to a matching object"""
            from pylav import EntryNotFoundError

            try:
                tags = await ctx.lavalink.radio_browser.tags()
            except EntryNotFoundError as e:
                raise commands.BadArgument(_("Tag with name `{arg}` not found").format(arg=arg)) from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), tags)):
                return r
            raise commands.BadArgument(_("Tag with name `{arg}` not found").format(arg=arg))

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[Tag]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            tags = await interaction.client.lavalink.radio_browser.tags()
            if not current:
                return [
                    Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                    for e in tags
                ][:25]

            async def _filter(c):
                return await asyncio.to_thread(fuzz.token_set_ratio, current, c.name)

            extracted = await heapq.nlargest(asyncstdlib.iter(tags), n=25, key=_filter)

            return [
                Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                for e in extracted
            ]

    class LanguageConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[Language]:
            """Converts a Language name to to a matching object"""
            from pylav import EntryNotFoundError

            try:
                langs = await ctx.lavalink.radio_browser.languages()
            except EntryNotFoundError as e:
                raise commands.BadArgument(_("Language with name `{arg}` not found").format(arg=arg)) from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), langs)):
                return r
            raise commands.BadArgument(_("Language with name `{arg}` not found").format(arg=arg))

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[Language]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            languages = await interaction.client.lavalink.radio_browser.languages()
            if not current:
                return [
                    Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                    for e in languages
                ][:25]

            async def _filter(c):
                return await asyncio.to_thread(fuzz.token_set_ratio, current, c.name)

            extracted = await heapq.nlargest(asyncstdlib.iter(languages), n=25, key=_filter)

            return [
                Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                for e in extracted
            ]

    class StateConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[State]:
            """Converts a State name to to a matching object"""
            from pylav import EntryNotFoundError

            try:
                states = await ctx.lavalink.radio_browser.states()
            except EntryNotFoundError as e:
                raise commands.BadArgument(_("State with name `{arg}` not found")) from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), states)):
                return r
            raise commands.BadArgument(_("State with name `{arg}` not found"))

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[State]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            data = interaction.data
            options = data.get("options", [])
            kwargs = {}
            if options:
                country = [v for v in options if v.get("name") == "country"]

                if country and (val := country[0].get("value")):
                    kwargs["country"] = val
            states = await interaction.client.lavalink.radio_browser.states(**kwargs)
            if not current:
                return [
                    Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                    for e in states
                ][:25]

            async def _filter(c):
                return await asyncio.to_thread(fuzz.token_set_ratio, current, c.name)

            extracted = await heapq.nlargest(asyncstdlib.iter(states), n=25, key=_filter)

            return [
                Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                for e in extracted
            ]

    class CodecConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[Codec]:
            """Converts a Codec name to to a matching object"""
            from pylav import EntryNotFoundError

            try:
                codecs = await ctx.lavalink.radio_browser.codecs()
            except EntryNotFoundError as e:
                raise commands.BadArgument(_("Codec with name `{arg}` not found").format(arg=arg)) from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), codecs)):
                return r
            raise commands.BadArgument(_("Codec with name `{arg}` not found").format(arg=arg))

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[Codec]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            codecs = await interaction.client.lavalink.radio_browser.codecs()
            if not current:
                return [
                    Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                    for e in codecs
                ][:25]

            async def _filter(c):
                return await asyncio.to_thread(fuzz.token_set_ratio, current, c.name)

            extracted = await heapq.nlargest(asyncstdlib.iter(codecs), n=25, key=_filter)

            return [
                Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                for e in extracted
            ]

    class CountryCodeConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[CountryCode]:
            """Converts a CountryCode name to to a matching object"""
            from pylav import EntryNotFoundError

            try:
                countrycodes = await ctx.lavalink.radio_browser.countrycodes()
            except EntryNotFoundError as e:
                raise commands.BadArgument(_("Country code `{arg}` not found").format(arg=arg)) from e

            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), countrycodes)):
                return r
            raise commands.BadArgument(_("Country code `{arg}` not found").format(arg=arg))

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[CountryCode]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            countrycodes = await interaction.client.lavalink.radio_browser.countrycodes()
            if not current:
                return [
                    Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                    for e in countrycodes
                ][:25]

            async def _filter(c):
                return await asyncio.to_thread(fuzz.token_set_ratio, current, c.name)

            extracted = await heapq.nlargest(asyncstdlib.iter(countrycodes), n=25, key=_filter)

            return [
                Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                for e in extracted
            ]

    class CountryConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[Country]:
            """Converts a Country name to to a matching object"""
            from pylav import EntryNotFoundError

            try:
                countries = await ctx.lavalink.radio_browser.countries()
            except EntryNotFoundError as e:
                raise commands.BadArgument(_("Country with name `{arg}` not found").format(arg=arg)) from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), countries)):
                return r
            raise commands.BadArgument(_("Country with name `{arg}` not found").format(arg=arg))

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[Country]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            data = interaction.data
            options = data.get("options", [])
            kwargs = {}
            if options:
                code = [v for v in options if v.get("name") in ["countrycode", "code"]]
                if code and (val := code[0].get("value")):
                    kwargs["code"] = val
            countries = await interaction.client.lavalink.radio_browser.countries(**kwargs)
            if not current:
                return [
                    Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                    for e in countries
                ][:25]

            async def _filter(c):
                return await asyncio.to_thread(fuzz.token_set_ratio, current, c.name)

            extracted = await heapq.nlargest(asyncstdlib.iter(countries), n=25, key=_filter)

            return [
                Choice(name=shorten_string(e.name, max_length=100) if e.name else _("Unnamed"), value=f"{e.name}")
                for e in extracted
            ]
