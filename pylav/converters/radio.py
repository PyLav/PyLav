from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from discord.app_commands import Choice, Transformer
from discord.ext import commands

from pylav.types import ContextT, InteractionT

if TYPE_CHECKING:
    from pylav.radio.objects import Codec, Country, CountryCode, Language, State, Station, Tag

    StationConverter = TypeVar("StationConverter", bound=Station)
    TagConverter = TypeVar("TagConverter", bound=Tag)
    LanguageConverter = TypeVar("LanguageConverter", bound=Language)
    StateConverter = TypeVar("StateConverter", bound=State)
    CodecConverter = TypeVar("CodecConverter", bound=Codec)
    CountryCodeConverter = TypeVar("CountryCodeConverter", bound=CountryCode)
    CountryConverter = TypeVar("CountryConverter", bound=Country)
else:

    class StationConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> Station:
            """Converts a station name or ID to a matching object."""
            from pylav import EntryNotFoundError

            try:
                stations = await ctx.lavalink.radio_browser.station_by_uuid(arg)
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Station with name or id `{arg}` not found.") from e
            if r := next(filter(lambda n: arg == f"{n.stationuuid}", stations), None):
                return r
            raise commands.BadArgument(f"Station with name or id `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> Station:
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            stations = await interaction.client.lavalink.radio_browser.search(name=current, limit=25)

            return [
                Choice(name=n.name or "Unnamed", value=f"{n.stationuuid}")
                for n in stations
                if current.lower() in n.name.lower()
            ][:25]

    class TagConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> Tag:
            """Converts a Tag name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                tags = await ctx.lavalink.radio_browser.tags(arg)
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Tag with name `{arg}` not found.") from e
            if r := next(filter(lambda n: arg == n.name, tags), None):
                return r
            raise commands.BadArgument(f"Tag with name `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> Tag:
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            tags = await interaction.client.lavalink.radio_browser.tags()

            return [
                Choice(name=n.name or "Unnamed", value=f"{n.name}") for n in tags if current.lower() in n.name.lower()
            ][:25]

    class LanguageConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> Language:
            """Converts a Language name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                tags = await ctx.lavalink.radio_browser.languages(arg)
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Language with name `{arg}` not found.") from e
            if r := next(filter(lambda n: arg == n.name, tags), None):
                return r
            raise commands.BadArgument(f"Language with name `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> Language:
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            languages = await interaction.client.lavalink.radio_browser.languages()

            return [
                Choice(name=n.name or "Unnamed", value=f"{n.name}")
                for n in languages
                if current.lower() in n.name.lower()
            ][:25]

    class StateConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> State:
            """Converts a State name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                states = await ctx.lavalink.radio_browser.states(arg)
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"State with name `{arg}` not found.") from e
            if r := next(filter(lambda n: arg == n.name, states), None):
                return r
            raise commands.BadArgument(f"State with name `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> State:
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            states = await interaction.client.lavalink.radio_browser.states()
            return [
                Choice(name=n.name or "Unnamed", value=f"{n.name}") for n in states if current.lower() in n.name.lower()
            ][:25]

    class CodecConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> Codec:
            """Converts a Codec name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                codecs = await ctx.lavalink.radio_browser.codecs(arg)
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Codec with name `{arg}` not found.") from e
            if r := next(filter(lambda n: arg == n.name, codecs), None):
                return r
            raise commands.BadArgument(f"Codec with name `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> Codec:
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            codecs = await interaction.client.lavalink.radio_browser.codecs()
            return [
                Choice(name=n.name or "Unnamed", value=f"{n.name}") for n in codecs if current.lower() in n.name.lower()
            ][:25]

    class CountryCodeConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> CountryCode:
            """Converts a CountryCode name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                countries = await ctx.lavalink.radio_browser.countrycodes(arg)
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Country with name `{arg}` not found.") from e

            if r := next(filter(lambda n: arg == n.name, countries), None):
                return r
            raise commands.BadArgument(f"Country with name `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> CountryCode:
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            countrycodes = await interaction.client.lavalink.radio_browser.countrycodes()
            return [
                Choice(name=n.name or "Unnamed", value=f"{n.name}")
                for n in countrycodes
                if current.lower() in n.name.lower()
            ][:25]

    class CountryConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> Country:
            """Converts a Country name to to a matching object."""
            from pylav import EntryNotFoundError

            try:
                countries = await ctx.lavalink.radio_browser.countries(arg)
            except EntryNotFoundError as e:
                raise commands.BadArgument(f"Country with name `{arg}` not found.") from e
            if r := next(filter(lambda n: arg == n.name, countries), None):
                return r
            raise commands.BadArgument(f"Country with name `{arg}` not found.")

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> Country:
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            countries = await interaction.client.lavalink.radio_browser.countries()
            return [
                Choice(name=n.name or "Unnamed", value=f"{n.name}")
                for n in countries
                if current.lower() in n.name.lower()
            ][:25]
