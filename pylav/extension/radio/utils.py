from __future__ import annotations

import heapq
import pathlib
import re
from collections.abc import Awaitable, Callable
from datetime import timedelta
from functools import wraps
from operator import attrgetter
from typing import TYPE_CHECKING, Any

from cashews import Cache
from discord.app_commands import Choice
from rapidfuzz import fuzz

from pylav.constants.radio import API_TYPES
from pylav.helpers.format.strings import shorten_string
from pylav.type_hints.generics import ANY_GENERIC_TYPE, PARAM_SPEC_TYPE

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLav", pathlib.Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


if TYPE_CHECKING:
    from pylav.core.client import Client, Translator
    from pylav.extension.radio.objects import Codec, Country, CountryCode, Language, State, Station, Tag


CACHE = Cache("TRANSFORMER_CACHE")
CACHE.setup("mem://?check_interval=10", size=1_000_000, enable=True)


class Error(Exception):
    """Base class for all exceptions raised by this module"""


class IllegalArgumentError(Error):
    """Raised for illegal argument"""


def bool_to_string(boolean: bool) -> str:
    """Convert a boolean type to string.

    Args:
        boolean (bool): A Boolean.

    Raises:
        TypeError

    Returns:
        str: String representation of a bool type.
    """
    string = str(boolean).lower()
    if string in {"true", "false"}:
        return string
    raise TypeError("Value must be True or False")


def snake_to_camel(string: str) -> str:
    """Convert a snake case string to camel case."""
    first, *others = string.split("_")
    return "".join([first.lower(), *map(str.title, others)])


def radio_browser_adapter(**kwargs: PARAM_SPEC_TYPE.kwargs) -> PARAM_SPEC_TYPE.kwargs:
    """Converts the keyword arguments to the format required by the RadioBrowser API."""
    params = {}

    for key, value in kwargs.items():
        new_key = snake_to_camel(key)
        if isinstance(kwargs[key], bool):
            value = bool_to_string(value)
        params[new_key] = value
    return params


def validate_input(
    type_value: dict[str, type[str | bool | int]] | dict[str, str | int | bool],
    input_data: PARAM_SPEC_TYPE.kwargs,
) -> None:
    """Validate the input data."""
    for key, value in input_data.items():
        try:
            key_type = type_value[key]
        except KeyError as exc:
            raise IllegalArgumentError(f"There is no parameter named '{exc.args[0]}'") from exc
        else:
            if not isinstance(value, key_type):
                raise TypeError(f"Argument {key!r} must be {key_type.__name__}, not {type(value).__name__}")


def type_check(
    func: Callable[PARAM_SPEC_TYPE, Awaitable[ANY_GENERIC_TYPE]]  # type: ignore
) -> Callable[PARAM_SPEC_TYPE, Awaitable[ANY_GENERIC_TYPE]]:  # type: ignore
    """Decorator to check the type of the input data."""

    @wraps(func)
    def wrapper(self, *args: PARAM_SPEC_TYPE.args, **kwargs: PARAM_SPEC_TYPE.kwargs) -> Awaitable[ANY_GENERIC_TYPE]:
        validate_input(API_TYPES[func.__name__], kwargs)
        kwargs = radio_browser_adapter(**kwargs)
        return func(self, *args, **kwargs)

    return wrapper


class TransformerCache:
    """A class to cache the data from the RadioBrowser API."""

    _cache_stations: dict[str, Station] = {}
    _cache_tags: dict[str, Tag] = {}
    _cache_languages: dict[str, Language] = {}
    _cache_states: dict[str, State] = {}
    _cache_codecs: dict[str, Codec] = {}
    _cache_country_codes: dict[str, CountryCode] = {}
    _cache_countries: dict[str, Country] = {}

    _choice_cache_stations: dict[str, Choice] = {}
    _choice_cache_tags: dict[str, Choice] = {}
    _choice_cache_languages: dict[str, Choice] = {}
    _choice_cache_states: dict[str, Choice] = {}
    _choice_cache_codecs: dict[str, Choice] = {}
    _choice_cache_country_codes: dict[str, Choice] = {}
    _choice_cache_countries: dict[str, Choice] = {}

    _top_25_stations: list[Choice] = []
    _client: Client | None = None

    @classmethod
    def clear_cache(cls):
        cls._cache_stations = {}
        cls._cache_tags = {}
        cls._cache_languages = {}
        cls._cache_states = {}
        cls._cache_codecs = {}
        cls._cache_country_codes = {}
        cls._cache_countries = {}
        cls._choice_cache_stations = {}
        cls._choice_cache_tags = {}
        cls._choice_cache_languages = {}
        cls._choice_cache_states = {}
        cls._choice_cache_codecs = {}
        cls._choice_cache_country_codes = {}
        cls._choice_cache_countries = {}

    @classmethod
    async def fill_cache(cls, client: Client):
        """Fill the cache with data from the RadioBrowser API."""
        cls._client = client
        cls._cache_stations = {
            s.stationuuid: s
            for s in sorted(
                await client.radio_browser.stations(hidebroken="true"), key=attrgetter("votes"), reverse=True
            )
        }
        cls._cache_tags = {t.name: t for t in sorted(await client.radio_browser.tags(), key=attrgetter("name"))}
        cls._cache_languages = {
            l.name: l for l in sorted(await client.radio_browser.languages(), key=attrgetter("name"))
        }
        cls._cache_states = {s.name: s for s in sorted(await client.radio_browser.states(), key=attrgetter("name"))}
        cls._cache_codecs = {c.name: c for c in sorted(await client.radio_browser.codecs(), key=attrgetter("name"))}
        cls._cache_country_codes = {
            c.name: c for c in sorted(await client.radio_browser.countrycodes(), key=attrgetter("name"))
        }
        cls._cache_countries = {
            c.name: c for c in sorted(await client.radio_browser.countries(), key=attrgetter("name"))
        }

    @classmethod
    def fill_choice_cache(cls):
        """Fill the choice cache with data from the cache."""
        cls._choice_cache_stations = {
            station.stationuuid: Choice(
                name=shorten_string(station.name, max_length=100)
                if station.name
                else shorten_string(max_length=100, string=_("Unnamed")),
                value=f"{station.stationuuid}",
            )
            for station in cls._cache_stations.values()
        }
        cls._choice_cache_tags = {
            tag.name: Choice(
                name=shorten_string(tag.name, max_length=100)
                if tag.name
                else shorten_string(max_length=100, string=_("Unnamed")),
                value=f"{tag.name}",
            )
            for tag in cls._cache_tags.values()
        }
        cls._choice_cache_languages = {
            language.name: Choice(
                name=shorten_string(language.name, max_length=100)
                if language.name
                else shorten_string(max_length=100, string=_("Unnamed")),
                value=f"{language.name}",
            )
            for language in cls._cache_languages.values()
        }
        cls._choice_cache_states = {
            state.name: Choice(
                name=shorten_string(state.name, max_length=100) if state.name else _("Unnamed"), value=f"{state.name}"
            )
            for state in cls._cache_states.values()
        }
        cls._choice_cache_codecs = {
            codec.name: Choice(
                name=shorten_string(codec.name, max_length=100) if codec.name else _("Unnamed"), value=f"{codec.name}"
            )
            for codec in cls._cache_codecs.values()
        }
        cls._choice_cache_country_codes = {
            country_code.name: Choice(
                name=shorten_string(country_code.name, max_length=100) if country_code.name else _("Unnamed"),
                value=f"{country_code.name}",
            )
            for country_code in cls._cache_country_codes.values()
        }
        cls._choice_cache_countries = {
            country.name: Choice(
                name=shorten_string(country.name, max_length=100) if country.name else _("Unnamed"),
                value=f"{country.name}",
            )
            for country in cls._cache_countries.values()
        }

    @classmethod
    def get_station_cache(cls) -> dict[str, Station]:
        """Get the station cache."""
        return cls._cache_stations

    @classmethod
    def get_tag_cache(cls) -> dict[str, Tag]:
        """Get the tag cache."""
        return cls._cache_tags

    @classmethod
    def get_language_cache(cls) -> dict[str, Language]:
        """Get the language cache."""
        return cls._cache_languages

    @classmethod
    def get_state_cache(cls) -> dict[str, State]:
        """Get the state cache."""
        return cls._cache_states

    @classmethod
    def get_codec_cache(cls) -> dict[str, Codec]:
        """Get the codec cache."""
        return cls._cache_codecs

    @classmethod
    def get_country_code_cache(cls) -> dict[str, CountryCode]:
        """Get the country code cache."""
        return cls._cache_country_codes

    @classmethod
    def get_country_cache(cls) -> dict[str, Country]:
        """Get the country cache."""
        return cls._cache_countries

    @classmethod
    @CACHE.cache(ttl=timedelta(hours=24))
    async def filter_cache(
        cls, cache_type: str, limit: int = 25, **kwargs: Any
    ) -> list[Station] | list[Tag] | list[Language] | list[State] | list[Codec] | list[CountryCode] | list[Country]:
        """Filter the cache by the given type and kwargs."""
        match cache_type:
            case "station":
                return await cls._filter_station_cache(limit=limit, **kwargs)
            case "tag":
                return await cls._filter_tag_cache(limit=limit, **kwargs)
            case "language":
                return await cls._filter_language_cache(limit=limit, **kwargs)
            case "state":
                return await cls._filter_state_cache(limit=limit, **kwargs)
            case "codec":
                return await cls._filter_codec_cache(limit=limit, **kwargs)
            case "countrycode":
                return await cls._filter_country_code_cache(limit=limit, **kwargs)
            case "country":
                return await cls._filter_country_cache(limit=limit, **kwargs)
            case __:
                return []

    @classmethod
    def build_filter(cls, **kwargs) -> dict[str, str | bool]:
        """Build a filter dict from the given kwargs."""
        filters = {}

        if "code" in kwargs:
            filters["code"] = kwargs["code"]
        if "country" in kwargs:
            filters["country"] = kwargs["country"]
            if kwargs["country"] in cls._choice_cache_country_codes:
                filters["country_exact"] = True
                kwargs["countrycode"] = cls._cache_countries[kwargs["country"]].iso_3166_1
        if "state" in kwargs:
            filters["state"] = kwargs["state"]
            if kwargs["state"] in cls._choice_cache_states:
                filters["state_exact"] = True
        if "language" in kwargs:
            filters["language"] = kwargs["language"]
            if kwargs["language"] in cls._choice_cache_languages:
                filters["language_exact"] = True
        if "tag" in kwargs:
            filters["tag"] = kwargs["tag"]
            if kwargs["tag"] in cls._choice_cache_tags:
                filters["tag_exact"] = True
        elif "tag_list" in kwargs:
            filters["tag_list"] = kwargs["tag_list"].split(",")
        if "order" in kwargs:
            filters["order"] = kwargs["order"]
        if "countrycode" in kwargs:
            filters["countrycode"] = kwargs["countrycode"]
        if "name" in kwargs:
            filters["name"] = re.sub(r"\s+", " ", kwargs["name"])
        return filters

    @classmethod
    @CACHE.cache(ttl=timedelta(hours=24))
    async def _filter_station_cache(cls, limit: int = 25, **kwargs: Any) -> list[Station]:
        filter_data = cls.build_filter(**kwargs)
        key_set = {
            "state_exact",
            "language_exact",
            "tag_exact",
            "countrycode",
            "state",
            "language",
            "tag",
            "tag_list",
            "name",
            "order",
        }

        search_args = {}
        for key in filter_data:
            if filter_data[key] is not None and key in key_set:
                data = filter_data[key]
                search_args[key] = ",".join(data) if key == "tag_list" else data
        station = await cls._client.radio_browser.search(
            limit=limit,
            **search_args,
        )

        def _sort(c: Station) -> float | list[float]:
            if "name" not in filter_data:
                return [-ord(c) for c in c.name]
            if c.name == filter_data["name"]:
                return 101
            return fuzz.partial_ratio(
                c.name,
                filter_data["name"],
            )

        return sorted(station, key=_sort, reverse=True)

    @classmethod
    @CACHE.cache(ttl=timedelta(hours=24))
    async def _filter_tag_cache(cls, limit: int = 25, **kwargs: Any) -> list[Tag]:
        filter_data = cls.build_filter(**kwargs)
        tag_exact = filter_data.pop("tag_exact", False)
        tag = filter_data.pop("tag", None)
        tag_list = filter_data.pop("tag_list", None)

        def _filter_tag(c: Tag) -> float:
            if (tag_exact and c.name == tag) or (tag_list and c.name in tag_list):
                return 101
            elif tag_list:
                return 0
            return fuzz.partial_ratio(
                c.name,
                tag,
            )

        def _filter(c: Tag) -> float:
            return _filter_tag(c)

        extracted: list[Tag] = heapq.nlargest(limit, cls.get_tag_cache().values(), key=_filter)

        return extracted

    @classmethod
    @CACHE.cache(ttl=timedelta(hours=24))
    async def _filter_country_cache(cls, limit: int = 25, **kwargs: Any) -> list[Country]:
        filter_data = cls.build_filter(**kwargs)
        country_exact = filter_data.pop("country_exact", False)
        country = filter_data.pop("country", None)
        countrycode = filter_data.pop("code", filter_data.pop("countrycode", None))

        def _filter_country(c: Country) -> float:
            if country_exact and c.name == country:
                return 101
            return fuzz.partial_ratio(
                c.name,
                country,
            )

        def _filter_countrycode(c: Country) -> float:
            return 101 if countrycode and c.iso_3166_1 == countrycode else 0

        def _filter(c: Country) -> float:
            result = (
                _filter_country(c) if country else 0,
                _filter_countrycode(c) if countrycode is None else 0,
            )
            return sum(result)

        extracted: list[Country] = heapq.nlargest(limit, cls.get_country_cache().values(), key=_filter)

        return extracted

    @classmethod
    @CACHE.cache(ttl=timedelta(hours=24))
    async def _filter_country_code_cache(cls, limit: int = 25, **kwargs: Any) -> list[CountryCode]:
        filter_data = cls.build_filter(**kwargs)
        countrycode = filter_data.pop("code", filter_data.pop("countrycode", None))

        def _filter_countrycode(c: CountryCode) -> int:
            return 101 if countrycode and c.name == countrycode else 0

        def _filter(c: CountryCode) -> int:
            return _filter_countrycode(c) if countrycode else 0

        extracted: list[CountryCode] = heapq.nlargest(limit, cls.get_country_code_cache().values(), key=_filter)

        return extracted

    @classmethod
    @CACHE.cache(ttl=timedelta(hours=24))
    async def _filter_state_cache(cls, limit: int = 25, **kwargs: Any) -> list[State]:
        filter_data = cls.build_filter(**kwargs)
        state_exact = filter_data.pop("state_exact", False)
        state = filter_data.pop("state", None)
        country = filter_data.pop("country", None)
        country_exact = filter_data.pop("country_exact", False)

        def _filter_state(c: State) -> float:
            if state_exact and c.name == state:
                return 101
            return fuzz.partial_ratio(
                c.name,
                state,
            )

        def _filter_country(c: State) -> float:
            if country_exact and c.country == country:
                return 101
            return fuzz.partial_ratio(
                c.country,
                country,
            )

        def _filter(c: State) -> float:
            result = (
                _filter_state(c) if state else 0,
                _filter_country(c) if country else 0,
            )
            return sum(result)

        extracted: list[State] = heapq.nlargest(limit, cls.get_state_cache().values(), key=_filter)

        return extracted

    @classmethod
    @CACHE.cache(ttl=timedelta(hours=24))
    async def _filter_language_cache(cls, limit: int = 25, **kwargs: Any) -> list[Language]:
        filter_data = cls.build_filter(**kwargs)
        language_exact = filter_data.pop("language_exact", False)
        language = filter_data.pop("language", None)

        def _filter_language(c: Language) -> float:
            if language_exact and c.name == language:
                return 101
            return fuzz.partial_ratio(
                c.name,
                language,
            )

        def _filter(c: Language) -> float:
            return _filter_language(c) if language else 0

        extracted: list[Language] = heapq.nlargest(limit, cls.get_language_cache().values(), key=_filter)

        return extracted

    @classmethod
    @CACHE.cache(ttl=timedelta(hours=24))
    async def _filter_codec_cache(cls, limit: int = 25, **kwargs: Any) -> list[Codec]:
        filter_data = cls.build_filter(**kwargs)
        codec_exact = filter_data.pop("codec_exact", False)
        codec = filter_data.pop("codec", None)

        def _filter_codec(c: Codec) -> float:
            if codec_exact and c.name == codec:
                return 101
            return fuzz.partial_ratio(
                c.name,
                codec,
            )

        def _filter(c: Codec) -> float:
            return _filter_codec(c) if codec else 0

        extracted: list[Codec] = heapq.nlargest(limit, cls.get_codec_cache().values(), key=_filter)

        return extracted

    @classmethod
    @CACHE.cache(ttl=timedelta(hours=24))
    async def get_top_25_stations(cls) -> list[Choice]:
        """Get the top 25 stations by vote count."""
        if cls._top_25_stations:
            return cls._top_25_stations

        def _filter(c: Station) -> int:
            return c.votes

        extracted: list[Station] = heapq.nlargest(25, cls.get_station_cache().values(), key=_filter)
        cls._top_25_stations = [
            Choice(
                name=shorten_string(e.name, max_length=100)
                if e.name
                else shorten_string(max_length=100, string=_("Unnamed")),
                value=f"{e.stationuuid}",
            )
            for e in extracted
        ]
        return cls._top_25_stations
