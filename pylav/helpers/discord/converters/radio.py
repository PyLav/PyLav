from __future__ import annotations

import random
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from discord.app_commands import Choice, Transformer
from discord.ext import commands

from pylav.exceptions.database import EntryNotFoundException
from pylav.extension.radio.objects import Codec, Country, CountryCode, Language, State, Station, Tag
from pylav.extension.radio.utils import TransformerCache
from pylav.helpers.format.strings import shorten_string
from pylav.logging import getLogger
from pylav.type_hints.bot import DISCORD_CONTEXT_TYPE, DISCORD_INTERACTION_TYPE

try:
    from redbot.core.i18n import Translator  # type: ignore

    _ = Translator("PyLav", Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


if TYPE_CHECKING:
    from discord.types.interactions import ChatInputApplicationCommandInteractionData

LOGGER = getLogger("PyLav.extension.Shared.converters.radio")

if TYPE_CHECKING:
    StationConverter = TypeVar("StationConverter", bound=list[Station])
    TagConverter = TypeVar("TagConverter", bound=list[Tag])
    LanguageConverter = TypeVar("LanguageConverter", bound=list[Language])
    StateConverter = TypeVar("StateConverter", bound=list[State])
    CodecConverter = TypeVar("CodecConverter", bound=list[Codec])
    CountryCodeConverter = TypeVar("CountryCodeConverter", bound=list[CountryCode])
    CountryConverter = TypeVar("CountryConverter", bound=list[Country])
else:

    class StationConverter(Transformer, TransformerCache):
        """Converts a station name to a matching object"""

        @classmethod
        async def convert(cls, ctx: DISCORD_CONTEXT_TYPE, arg: str) -> list[Station]:
            """Converts a station name to a matching object"""
            if ctx.bot.pylav.radio_browser.disabled:
                return []

            try:
                if arg in cls._cache_stations:
                    return [cls._cache_stations[arg]]
                return await cls.filter_cache(cache_type="station", limit=25, name=arg)
            except EntryNotFoundException as e:
                raise commands.BadArgument(
                    _("A station with the name `{user_input_variable_do_not_translate}` was not found.").format(
                        user_input_variable_do_not_translate=arg
                    )
                ) from e

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> list[Station]:
            """Transforms a station name to a matching object"""
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            if interaction.client.pylav.radio_browser.disabled:
                return []
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            """Autocompletes a station name to a matching object"""
            if interaction.client.pylav.radio_browser.disabled:
                return [
                    Choice(
                        name=shorten_string(
                            max_length=100, string=_("The Radio Browser extension is currently disabled.")
                        ),
                        value="???",
                    )
                ]
            data = interaction.data
            kwargs = cls.process_kwargs(current, data)
            if not current and not kwargs:
                return await cls.get_top_25_stations()
            kwargs["order"] = "votes"
            stations = await cls.filter_cache(cache_type="station", limit=25, **kwargs)
            for station in stations:
                cls.maybe_add_station_to_cache(station)
            return [cls._choice_cache_stations[stations.stationuuid] for stations in stations]

        @classmethod
        def maybe_add_station_to_cache(cls, station: Station) -> None:
            """Adds a station to the cache if it's not already in it"""
            if station.stationuuid not in cls._choice_cache_stations:
                cls._choice_cache_stations[station.stationuuid] = Choice(
                    name=shorten_string(station.name, max_length=100)
                    if station.name
                    else shorten_string(max_length=100, string=_("Unnamed")),
                    value=f"{station.stationuuid}",
                )
                cls._cache_stations[station.stationuuid] = station

        @staticmethod
        def process_kwargs(
            current: str,
            data: ChatInputApplicationCommandInteractionData | None,
        ) -> dict[str, Any]:
            """Processes the kwargs for the autocomplete method"""
            kwargs = {}
            if options := data.get("options", []):
                country_code = [v for v in options if v.get("name") == "countrycode"]
                country = [v for v in options if v.get("name") == "country"]
                state = [v for v in options if v.get("name") == "state"]
                language = [v for v in options if v.get("name") == "language"]
                tags = [v for v in options if v.get("name", "").startswith("tag")]
                if country_code and (val := country_code[0].get("value")):
                    kwargs["countrycode"] = val
                if country and (val := country[0].get("value")):
                    kwargs["country"] = val
                if state and (val := state[0].get("value")):
                    kwargs["state"] = val
                if language and (val := language[0].get("value")):
                    kwargs["language"] = val
                if tags:
                    if len(tags) == 1 and (val := tags[0].get("value")):
                        kwargs["tag"] = val
                    elif len(tags) > 1:
                        kwargs["tag_list"] = ",".join([tv for t in tags if (tv := t.get("value"))])
            if current:
                kwargs["name"] = current
            return kwargs

    class TagConverter(Transformer, TransformerCache):
        """Converts a Tag name to to a matching object"""

        @classmethod
        async def convert(cls, ctx: DISCORD_CONTEXT_TYPE, arg: str) -> list[Tag]:
            """Converts a Tag name to to a matching object"""
            if ctx.bot.pylav.radio_browser.disabled:
                return []

            try:
                if arg in cls._cache_tags:
                    return [cls._cache_tags[arg]]
                return await cls.filter_cache(cache_type="tag", limit=25, tag=arg)
            except EntryNotFoundException as e:
                raise commands.BadArgument(
                    _("A tag with the name `{user_input_variable_do_not_translate}` was not found.").format(
                        user_input_variable_do_not_translate=arg
                    )
                ) from e

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> list[Tag]:
            """Transforms a Tag name to to a matching object"""
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            if interaction.client.pylav.radio_browser.disabled:
                return []
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            """Autocompletes a Tag name to to a matching object"""
            if interaction.client.pylav.radio_browser.disabled:
                return [
                    Choice(
                        name=shorten_string(
                            max_length=100, string=_("The Radio Browser extension is currently disabled.")
                        ),
                        value="???",
                    )
                ]

            if not current:
                return random.choices(list(cls._choice_cache_tags.values()), k=25)

            tags = await cls.filter_cache(cache_type="tag", limit=25, tag=current)

            return [cls._choice_cache_tags[tag.name] for tag in tags]

    class LanguageConverter(Transformer, TransformerCache):
        """Converts a Language name to to a matching object"""

        @classmethod
        async def convert(cls, ctx: DISCORD_CONTEXT_TYPE, arg: str) -> list[Language]:
            """Converts a Language name to to a matching object"""
            if ctx.bot.pylav.radio_browser.disabled:
                return []

            try:
                if arg in cls._cache_languages:
                    return [cls._cache_languages[arg]]
                return await cls.filter_cache(cache_type="language", limit=25, language=arg)
            except EntryNotFoundException as e:
                raise commands.BadArgument(
                    _("A language with the name `{user_input_variable_do_not_translate}` was not found.").format(
                        user_input_variable_do_not_translate=arg
                    )
                ) from e

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> list[Language]:
            """Transforms a Language name to to a matching object"""
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            if interaction.client.pylav.radio_browser.disabled:
                return []
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            """Autocompletes a Language name to to a matching object"""
            if interaction.client.pylav.radio_browser.disabled:
                return [
                    Choice(
                        name=shorten_string(
                            max_length=100, string=_("The Radio Browser extension is currently disabled.")
                        ),
                        value="???",
                    )
                ]
            if not current:
                return random.choices(list(cls._choice_cache_languages.values()), k=25)

            languages = await cls.filter_cache(cache_type="language", limit=25, language=current)

            return [cls._choice_cache_languages[language.name] for language in languages]

    class StateConverter(Transformer, TransformerCache):
        """Converts a State name to to a matching object"""

        @classmethod
        async def convert(cls, ctx: DISCORD_CONTEXT_TYPE, arg: str) -> list[State]:
            """Converts a State name to to a matching object"""
            if ctx.bot.pylav.radio_browser.disabled:
                return []
            try:
                if arg in cls._cache_states:
                    return [cls._cache_states[arg]]
                return await cls.filter_cache(cache_type="state", limit=25, state=arg)
            except EntryNotFoundException as e:
                raise commands.BadArgument(
                    _("A state with the name `{user_input_variable_do_not_translate}` was not found.").format(
                        user_input_variable_do_not_translate=arg
                    )
                ) from e

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> list[State]:
            """Transforms a State name to to a matching object"""
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            if interaction.client.pylav.radio_browser.disabled:
                return []
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            """Autocompletes a State name to to a matching object"""
            if interaction.client.pylav.radio_browser.disabled:
                return [
                    Choice(
                        name=shorten_string(
                            max_length=100, string=_("The Radio Browser extension is currently disabled.")
                        ),
                        value="???",
                    )
                ]
            if not current:
                return random.choices(list(cls._choice_cache_states.values()), k=25)
            states = await cls.filter_cache(cache_type="state", limit=25, state=current)
            return [cls._choice_cache_states[state.name] for state in states]

    class CodecConverter(Transformer, TransformerCache):
        """Converts a Codec name to to a matching object"""

        @classmethod
        async def convert(cls, ctx: DISCORD_CONTEXT_TYPE, arg: str) -> list[Codec]:
            """Converts a Codec name to to a matching object"""
            if ctx.bot.pylav.radio_browser.disabled:
                return []

            try:
                if arg in cls._cache_codecs:
                    return [cls._cache_codecs[arg]]
                return await cls.filter_cache(cache_type="codec", limit=25, codec=arg)
            except EntryNotFoundException as e:
                raise commands.BadArgument(
                    _("A codec with the name `{user_input_variable_do_not_translate}` was not found.").format(
                        user_input_variable_do_not_translate=arg
                    )
                ) from e

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> list[Codec]:
            """Transforms a Codec name to to a matching object"""
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            if interaction.client.pylav.radio_browser.disabled:
                return []
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            """Autocompletes a Codec name to to a matching object"""
            if interaction.client.pylav.radio_browser.disabled:
                return [
                    Choice(
                        name=shorten_string(
                            max_length=100, string=_("The Radio Browser extension is currently disabled.")
                        ),
                        value="???",
                    )
                ]
            if not current:
                return random.choices(list(cls._choice_cache_codecs.values()), k=25)
            codecs = await cls.filter_cache(cache_type="codec", limit=25, codec=current)
            return [cls._choice_cache_codecs[codec.name] for codec in codecs]

    class CountryCodeConverter(Transformer, TransformerCache):
        """Converts a Country Code name to to a matching object"""

        @classmethod
        async def convert(cls, ctx: DISCORD_CONTEXT_TYPE, arg: str) -> list[CountryCode]:
            """Converts a CountryCode name to to a matching object"""
            if ctx.bot.pylav.radio_browser.disabled:
                return []

            try:
                if arg in cls._cache_country_codes:
                    return [cls._cache_country_codes[arg]]
                return await cls.filter_cache(cache_type="countrycode", limit=25, countrycode=arg)
            except EntryNotFoundException as e:
                raise commands.BadArgument(
                    _("A country code with the value `{user_input_variable_do_not_translate}` was not found.").format(
                        user_input_variable_do_not_translate=arg
                    )
                ) from e

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> list[CountryCode]:
            """Transforms a Country Code name to to a matching object"""
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            if interaction.client.pylav.radio_browser.disabled:
                return []
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            """Autocompletes a Country Code name to to a matching object"""
            if interaction.client.pylav.radio_browser.disabled:
                return [
                    Choice(
                        name=shorten_string(
                            max_length=100, string=_("The Radio Browser extension is currently disabled.")
                        ),
                        value="???",
                    )
                ]
            if not current:
                return random.choices(list(cls._choice_cache_country_codes.values()), k=25)
            country_codes = await cls.filter_cache(cache_type="countrycode", limit=25, countrycode=current)
            return [cls._choice_cache_country_codes[country_code.name] for country_code in country_codes]

    class CountryConverter(Transformer, TransformerCache):
        """Converts a Country name to to a matching object"""

        @classmethod
        async def convert(cls, ctx: DISCORD_CONTEXT_TYPE, arg: str) -> list[Country]:
            """Converts a Country name to to a matching object"""
            if ctx.bot.pylav.radio_browser.disabled:
                return []

            try:
                if arg in cls._cache_countries:
                    return [cls._cache_countries[arg]]
                return await cls.filter_cache(cache_type="country", limit=25, country=arg)
            except EntryNotFoundException as e:
                raise commands.BadArgument(
                    _("A country with the name `{user_input_variable_do_not_translate}` was not found.").format(
                        user_input_variable_do_not_translate=arg
                    )
                ) from e

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> list[Country]:
            """Transforms a Country name to to a matching object"""
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            if interaction.client.pylav.radio_browser.disabled:
                return []
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            """Autocompletes a Country name to to a matching object"""
            if interaction.client.pylav.radio_browser.disabled:
                return [
                    Choice(
                        name=shorten_string(
                            max_length=100, string=_("The Radio Browser extension is currently disabled.")
                        ),
                        value="???",
                    )
                ]
            data = interaction.data
            options = data.get("options", [])
            kwargs = {}
            if options:
                code = [v for v in options if v.get("name") in ["countrycode", "code"]]
                if code and (val := code[0].get("value")):
                    kwargs["countrycode"] = val

            countries = await cls.filter_cache(cache_type="country", limit=25, country=current, **kwargs)
            return [cls._choice_cache_countries[country.name] for country in countries]
