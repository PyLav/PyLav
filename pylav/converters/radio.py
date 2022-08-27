from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import asyncstdlib
from discord.app_commands import Choice, Transformer
from discord.ext import commands

from pylav import getLogger
from pylav.types import ContextT, InteractionT

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
            """Converts a station name to a matching object."""
            from pylav import EntryNotFoundError

            try:
                stations = await ctx.lavalink.radio_browser.stations()
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Station with name `{arg}` not found.") from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), stations)):
                return r
            raise commands.BadArgument(f"Station with name `{arg}` not found.")

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
            kwargs = {"order": "clickcount"}
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
                        kwargs["tag_list"] = [tv for t in tags if (tv := t.get("value"))]

            if current:
                kwargs["name"] = current
            stations = await interaction.client.lavalink.radio_browser.search(limit=25, **kwargs)
            return [
                Choice(name=n.name[:99] if n.name else "Unnamed", value=f"{n.name}")
                for n in stations
                if current.lower() in n.name.lower()
            ][:25]

    class TagConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[Tag]:
            """Converts a Tag name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                tags = await ctx.lavalink.radio_browser.tags()
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Tag with name `{arg}` not found.") from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), tags)):
                return r
            raise commands.BadArgument(f"Tag with name `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[Tag]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            tags = await interaction.client.lavalink.radio_browser.tags()
            return [
                Choice(name=n.name[:99] if n.name else "Unnamed", value=f"{n.name}")
                for n in tags
                if current.lower() in n.name.lower()
            ][:25]

    class LanguageConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[Language]:
            """Converts a Language name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                langs = await ctx.lavalink.radio_browser.languages()
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Language with name `{arg}` not found.") from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), langs)):
                return r
            raise commands.BadArgument(f"Language with name `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[Language]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            languages = await interaction.client.lavalink.radio_browser.languages()

            return [
                Choice(name=n.name[:99] if n.name else "Unnamed", value=f"{n.name}")
                for n in languages
                if current.lower() in n.name.lower()
            ][:25]

    class StateConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[State]:
            """Converts a State name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                states = await ctx.lavalink.radio_browser.states()
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"State with name `{arg}` not found.") from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), states)):
                return r
            raise commands.BadArgument(f"State with name `{arg}` not found.")

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
            LOGGER.debug(f"StateConverter Autocompleting {current} with {kwargs} and {options}")

            states = await interaction.client.lavalink.radio_browser.states(**kwargs)
            return [
                Choice(name=n.name[:99] if n.name else "Unnamed", value=f"{n.name}")
                for n in states
                if current.lower() in n.name.lower()
            ][:25]

    class CodecConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[Codec]:
            """Converts a Codec name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                codecs = await ctx.lavalink.radio_browser.codecs()
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Codec with name `{arg}` not found.") from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), codecs)):
                return r
            raise commands.BadArgument(f"Codec with name `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[Codec]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            codecs = await interaction.client.lavalink.radio_browser.codecs()
            return [
                Choice(name=n.name[:99] if n.name else "Unnamed", value=f"{n.name}")
                for n in codecs
                if current.lower() in n.name.lower()
            ][:25]

    class CountryCodeConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[CountryCode]:
            """Converts a CountryCode name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                countrycodes = await ctx.lavalink.radio_browser.countrycodes()
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Country code `{arg}` not found.") from e

            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), countrycodes)):
                return r
            raise commands.BadArgument(f"Country code `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> list[CountryCode]:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            countrycodes = await interaction.client.lavalink.radio_browser.countrycodes()
            return [
                Choice(name=n.name[:99] if n.name else "Unnamed", value=f"{n.name}")
                for n in countrycodes
                if current.lower() in n.name.lower()
            ][:25]

    class CountryConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> list[Country]:
            """Converts a Country name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                countries = await ctx.lavalink.radio_browser.countries()
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Country with name `{arg}` not found.") from e
            if r := await asyncstdlib.list(asyncstdlib.filter(lambda n: arg.lower() in n.name.lower(), countries)):
                return r
            raise commands.BadArgument(f"Country with name `{arg}` not found.")

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
            return [
                Choice(name=n.name[:99] if n.name else "Unnamed", value=f"{n.name}")
                for n in countries
                if current.lower() in n.name.lower()
            ][:25]
