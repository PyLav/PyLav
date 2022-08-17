from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import asyncstdlib
from discord.app_commands import Choice, Transformer
from discord.ext import commands

from pylav.types import ContextT, InteractionT

if TYPE_CHECKING:
    from pylav.radio.objects import Codec, Country, CountryCode, Language, State, Station, Tag

    StationConverter = TypeVar("StationConverter", bound=list[Station])
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
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
            stations = await interaction.client.lavalink.radio_browser.search(name=current, limit=25)

            return [
                Choice(name=n.name or "Unnamed", value=f"{n.name}")
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
