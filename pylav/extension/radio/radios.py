from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import aiohttp
import aiohttp_client_cache
from yarl import URL

from pylav.compat import json
from pylav.extension.radio.base_url import pick_base_url
from pylav.extension.radio.objects import Codec, Country, CountryCode, Language, State, Station, Tag
from pylav.extension.radio.utils import TransformerCache, type_check
from pylav.logging import getLogger
from pylav.type_hints.dict_typing import JSON_DICT_TYPE
from pylav.utils.vendor.redbot import AsyncIter

if TYPE_CHECKING:
    from pylav.core.client import Client

LOGGER = getLogger("PyLav.extension.RadioBrowser")


class Request:
    """A wrapper for the aiohttp client."""

    __slots__ = ("_headers", "_cached_session", "_session")

    def __init__(
        self,
        headers: dict[str, str] | None = None,
        cached_session: aiohttp_client_cache.CachedSession | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._headers = headers
        self._cached_session = cached_session
        self._session = session

    async def get(self, url: str | URL, skip_cache: bool = False, **kwargs: Any) -> list[JSON_DICT_TYPE] | None:
        if skip_cache:
            async with self._session.get(url, params=kwargs) as resp:
                if resp.status == 200:
                    return await resp.json(loads=json.loads)
        else:
            async with self._cached_session.get(url, headers=self._headers, params=kwargs) as resp:
                if resp.status == 200:
                    return await resp.json(loads=json.loads)
        resp.raise_for_status()


class RadioBrowser:
    """This class implements the main interface for the Radio Browser API."""

    def __init__(self, client: Client) -> None:
        headers = {"User-Agent": f"PyLav/{client.lib_version}"}
        self._client = client
        self.request = Request(
            headers=headers, cached_session=self._client.cached_session, session=self._client.session
        )
        self._disabled = False

    async def initialize(self) -> None:
        try:
            self._disabled = not await self.base_url
            if self._disabled:
                LOGGER.error("Error while initializing the Radio Browser extension - disabling it")
                return
            LOGGER.debug("Priming radio cache")
            await TransformerCache.fill_cache(self._client)
            await self.stations_by_clicks(limit=25)
            await self.stations_by_votes(limit=25)
            TransformerCache.fill_choice_cache()
            LOGGER.debug("Radio cache primed")
        except Exception as e:
            LOGGER.error("Error while initializing the Radio Browser extension - disabling it")
            LOGGER.debug(e, exc_info=e)
            self._disabled = True

    @property
    async def base_url(self) -> URL:
        """The base URL for the Radio Browser API."""
        if url := await pick_base_url(self._client.session):
            return url
        self._disabled = True
        return URL()

    @property
    def disabled(self) -> bool:
        """Whether the extension is disabled."""
        return self._disabled

    @type_check
    async def countries(self, code: str | None = None) -> list[Country]:
        """Lists all countries.

        Args:
            code (str, optional): Filter by country code. Defaults to None.

        Returns:
            list: Countries.

        See details:
            https://de1.api.radio-browser.info/#List_of_countries
        """
        url = await self.base_url / "json" / "countries"
        if code:
            url /= code
        if self._disabled:
            return []
        return [Country(**country) for country in await self.request.get(url, hidebroken="true")]

    @type_check
    async def countrycodes(self, code: str | None = None) -> list[CountryCode]:
        """Lists all countries.

        Args:
            code (str, optional): Filter by country code. Defaults to None.

        Returns:
            list: Countries.

        See details:
            https://de1.api.radio-browser.info/#List_of_countrycodes
        """
        url = await self.base_url / "json" / "countrycodes"
        if code:
            url /= code
        if self._disabled:
            return []
        return [CountryCode(**country) for country in await self.request.get(url, hidebroken="true")]

    @type_check
    async def codecs(self, codec: str | None = None) -> list[Codec]:
        """Lists all codecs.

        Args:
            codec (str, optional): Filter by codec. Defaults to None.

        Returns:
            list: Codecs.

        See details:
            https://de1.api.radio-browser.info/#List_of_codecs
        """
        url = await self.base_url / "json" / "codecs"
        if self._disabled:
            return []
        response = await self.request.get(url, hidebroken="true")
        if codec:
            return [Codec(**tag) for tag in filter(lambda s: s["name"].lower() == codec.lower(), response)]
        return [Codec(**tag) for tag in response]

    @type_check
    async def states(self, country: str | None = None, state: str | None = None) -> list[State]:
        """Lists all states.

        Args:
            country (str, optional): Filter by country. Defaults to None.
            state (str, optionla): Filter by state. Defaults to None.

        Returns:
            list: States.

        See details:
            https://de1.api.radio-browser.info/#List_of_states
        """
        url = await self.base_url / "json" / "states"
        if self._disabled:
            return []
        response = await self.request.get(url, hidebroken="true")

        if country:
            if state:
                return [
                    State(**state)
                    for state in filter(
                        lambda s: s["country"].lower() == country.lower() and s["name"].lower() == state.lower(),
                        response,
                    )
                ]
            return [State(**state) for state in filter(lambda s: s["country"].lower() == country.lower(), response)]
        if state:
            return [State(**state) for state in filter(lambda s: s["name"].lower() == state.lower(), response)]
        return [State(**state) for state in response]

    @type_check
    async def languages(self, language: str | None = None) -> list[Language]:
        """Lists all languages.

        Args:
            language (str, optional): Filter by language. Defaults to None.

        Returns:
            list: Languages.

        See details:
            https://de1.api.radio-browser.info/#List_of_languages
        """
        url = await self.base_url / "json" / "languages"
        if language:
            url /= language
        if self._disabled:
            return []
        response = await self.request.get(url, hidebroken="true")
        return [Language(**language) for language in response]

    @type_check
    async def tags(self, tag: str | None = None) -> list[Tag]:
        """Lists all tags.

        Args:
            tag (str, optional): Filter by tag. Defaults to None.

        Returns:
            list: Tags.

        See details:
            https://de1.api.radio-browser.info/#List_of_tags
        """
        url = await self.base_url / "json" / "tags"
        if tag:
            url /= tag.lower()
        if self._disabled:
            return []
        response = await self.request.get(url, hidebroken="true")
        return [Tag(**tag) for tag in response]

    async def station_by_uuid(self, stationuuid: str) -> list[Station]:
        """Radio station by stationuuid.

        Args:
            stationuuid (str): A globally unique identifier for the station.

        Returns:
            list: Stations.

        See details:
            https://de1.api.radio-browser.info/#List_of_radio_stations
        """
        url = await self.base_url / "json" / "stations" / "byuuid" / stationuuid
        if self._disabled:
            return []
        response = await self.request.get(url, hidebroken="true")
        return [Station(radio_api_client=self, **station) async for station in AsyncIter(response, steps=250)]

    async def stations_by_name(
        self, name: str, exact: bool = False, **kwargs: str | int | bool | None
    ) -> list[Station]:
        """Lists all radio stations by name.

        Args:
            name (str): The name of the station.
            exact (bool): if the search should search for a station with the exact `name`

        Returns:
            list: Stations.

        See details:
            https://de1.api.radio-browser.info/#List_of_radio_stations
        """
        kwargs |= {"name": name, "name_exact": exact, "order": "votes"}
        kwargs["hidebroken"] = kwargs.pop("hidebroken", True)
        return await self.search(**kwargs)

    async def stations_by_codec(
        self, codec: str, exact: bool = False, **kwargs: str | int | bool | None
    ) -> list[Station]:
        """Lists all radio stations by codec.

        Args:
            codec (str): The name of the codec.
            exact (bool): if the search should search for a station with the exact `codec`

        Returns:
            list: Stations.

        See details:
            https://de1.api.radio-browser.info/#List_of_radio_stations
        """
        kwargs |= {"codec": codec, "codec_exact": exact, "order": "votes"}
        kwargs["hidebroken"] = kwargs.pop("hidebroken", True)
        return await self.search(**kwargs)

    async def stations_by_country(
        self, country: str, exact: bool = False, **kwargs: str | int | bool | None
    ) -> list[Station]:
        """Lists all radio stations by country.

        Args:
            country (str): The name of the country.
            exact (bool): if the search should search for a station with the exact `country`

        Returns:
            list: Stations.

        See details:
            https://de1.api.radio-browser.info/#List_of_radio_stations
        """
        kwargs |= {"country": country, "country_exact": exact, "order": "votes"}
        kwargs["hidebroken"] = kwargs.pop("hidebroken", True)
        return await self.search(**kwargs)

    async def stations_by_countrycode(self, code: str, **kwargs: str | int | bool | None) -> list[Station]:
        """Lists all radio stations by country code.

        Arguments:
        ----------
            code (str): Official countrycodes as in ISO 3166-1 alpha-2.
            exact (bool): if the search should search for a station with the exact `code`

        Returns:
            list: Stations.

        See details:
            https://de1.api.radio-browser.info/#List_of_radio_stations
        """
        kwargs |= {"countrycode": code, "order": "votes"}
        kwargs["hidebroken"] = kwargs.pop("hidebroken", True)
        return await self.search(**kwargs)

    async def stations_by_state(
        self, state: str, exact: bool = False, **kwargs: str | int | bool | None
    ) -> list[Station]:
        """Lists all radio stations by state.

        Args:
            state (str): The name of the state.
            exact (bool): if the search should search for a station with the exact `state`

        Returns:
            list: Stations.

        See details:
            https://de1.api.radio-browser.info/#List_of_radio_stations
        """
        kwargs |= {"state": state, "state_exact": exact, "order": "votes"}
        kwargs["hidebroken"] = kwargs.pop("hidebroken", True)
        return await self.search(**kwargs)

    async def stations_by_language(
        self, language: str, exact: bool = False, **kwargs: str | int | bool | None
    ) -> list[Station]:
        """Lists all radio stations by language.

        Args:
            language (str): The name of the language.
            exact (bool): if the search should search for a station with the exact `language`

        Returns:
            list: Stations.

        See details:
            https://de1.api.radio-browser.info/#List_of_radio_stations
        """
        kwargs |= {"language": language, "language_exact": exact, "order": "votes"}
        kwargs["hidebroken"] = kwargs.pop("hidebroken", True)
        return await self.search(**kwargs)

    async def stations_by_tag(self, tag: str, exact: bool = False, **kwargs: str | int | bool | None) -> list[Station]:
        """Lists all radio stations by tag.

        Args:
            tag (str): The name of the tag.
            exact (bool): If set to True, the tag must be exactly the same as the given tag.
        Returns:
            list: Stations.
        See details:
            https://de1.api.radio-browser.info/#List_of_radio_stations
        """
        kwargs |= {"tag": tag, "tag_exact": exact, "order": "votes"}
        kwargs["hidebroken"] = kwargs.pop("hidebroken", True)
        return await self.search(**kwargs)

    async def stations_by_tag_list(self, tag_list: list[str], **kwargs: str | int | bool | None) -> list[Station]:
        """Lists all radio stations by tag. Must match all tags exactly.

        Args:
            tag_list (list): A list of names of tags.

        Returns:
            list: Stations.
        See details:
            https://de1.api.radio-browser.info/#List_of_radio_stations
        """
        tag_list = ",".join(tag_list)
        kwargs["tag_list"] = tag_list
        kwargs |= {"tag_list": tag_list, "order": "votes"}
        kwargs["hidebroken"] = kwargs.pop("hidebroken", True)
        return await self.search(**kwargs)

    async def click_counter(self, stationuuid: str) -> list[dict[str, str | int | bool]]:
        """Increase the click count of a station by one.

        This should be called everytime when a user starts
        playing a stream to mark the stream more popular than others.
        Every call to this endpoint from the same IP address and for
        the same station only gets counted once per day. The call will
        return detailed information about the stat stream, supported output
        formats: JSON

        Args:
            stationuuid (str): A globally unique identifier for the station.

        Returns:
            dict: A dict containing informations about the radio station.

        See details:
            https://de1.api.radio-browser.info/#Count_station_click
        """
        url = await self.base_url / "json" / "url" / f"{stationuuid}"
        return [] if self._disabled else await self.request.get(url, hidebroken="true")

    async def stations(self, **kwargs: str | int | bool | None) -> list[Station]:
        """Lists all radio stations.

        Returns:
            list: Stations.

        See details:
            https://nl1.api.radio-browser.info/#List_of_all_radio_stations
        """
        url = await self.base_url / "json" / "stations"
        if self._disabled:
            return []
        kwargs["hidebroken"] = kwargs.pop("hidebroken", "true")
        return [
            Station(radio_api_client=self, **station)
            async for station in AsyncIter(await self.request.get(url, **kwargs), steps=250)
        ]

    async def stations_by_votes(self, limit: int, **kwargs: str | int | bool | None) -> list[Station]:
        """A list of the highest-voted stations.

        Args:
            limit: Number of wanted stations

        Returns:
            list: Stations.

        See details:
            https://nl1.api.radio-browser.info/#Stations_by_votes
        """
        url = await self.base_url / "json" / "stations" / "topvote" / f"{limit}"
        if self._disabled:
            return []
        kwargs["hidebroken"] = kwargs.pop("hidebroken", "true")
        response = await self.request.get(url, **kwargs)
        return [Station(radio_api_client=self, **station) async for station in AsyncIter(response, steps=250)]

    async def stations_by_clicks(self, limit: int, **kwargs: str | int | bool | None) -> list[Station]:
        """A list of the stations that are clicked the most.

        Args:
            limit: Number of wanted stations

        Returns:
            list: Stations.

        See details:
            https://nl1.api.radio-browser.info/#Stations_by_clicks
        """
        url = await self.base_url / "json" / "stations" / "topclick" / f"{limit}"
        if self._disabled:
            return []
        kwargs["hidebroken"] = kwargs.pop("hidebroken", "true")
        response = await self.request.get(url, **kwargs)
        return [Station(radio_api_client=self, **station) async for station in AsyncIter(response, steps=250)]

    @type_check
    async def search(self, **kwargs: str | int | bool | None) -> list[Station]:
        """Advanced search.

        It will search for the station whose attribute
        contains the search term.

        Arguments:
        ----------
            name (str, optional): Name of the station.
            name_exact (bool, optional): Only exact matches, otherwise all
                matches (default: False).
            country (str, optional): Country of the station.
            country_exact (bool, optional): Only exact matches, otherwise
                all matches (default: False).
            countrycode (str, optional): 2-digit countrycode of the station
                (see ISO 3166-1 alpha-2)
            state (str, optional): State of the station.
            state_exact (bool, optional): Only exact matches, otherwise all
                matches. (default: False)
            language (str, optional): Language of the station.
            language_exact (bool, optional): Only exact matches, otherwise
                all matches. (default: False)
            tag (str, optional): Tag of the station.
            tag_exact (bool, optional): Only exact matches, otherwise all
                matches. (default: False)
            tag_list (str, optional): A comma-separated list of tag.
            bitrate_min (int, optional): Minimum of kbps for bitrate field of
                stations in result. (default: 0)
            bitrate_max (int, optional): Maximum of kbps for bitrate field of
                stations in result. (default: 1000000)
            order (str, optional): The result list will be sorted by: name,
                url, homepage, favicon, tags, country, state, language, votes,
                codec, bitrate, lastcheckok, lastchecktime, clicktimestamp,
                clickcount, clicktrend, random
            reverse (bool, optional): Reverse the result list if set to true.
                (default: false)
            offset (int, optional): Starting value of the result list from
                the database. For example, if you want to do paging on the
                server side. (default: 0)
            limit (int, optional): Number of returned datarows (stations)
                starting with offset (default 100000)
            hidebroken (bool, optional): do list/not list broken stations.
                Note: Not documented in the "Advanced Station Search".

        Returns:
            list: Station.

        See details:
            https://de1.api.radio-browser.info/#Advanced_station_search
        """
        url = await self.base_url / "json" / "stations" / "search"
        if self._disabled:
            return []
        # lowercase tag reference since the API turned to be case-sensitive
        for paramkey in ["tag", "tagList"]:
            if paramkey in kwargs:
                kwargs[paramkey] = kwargs[paramkey].lower()
        kwargs["hidebroken"] = kwargs.pop("hidebroken", "true")
        if kwargs["hidebroken"] is False:
            kwargs["hidebroken"] = "false"
        return [
            Station(radio_api_client=self, **station)
            async for station in AsyncIter(await self.request.get(url, **kwargs), steps=250)
        ]

    async def click(self, station: Station | None = None, station_id: str | None = None) -> None:
        """Increase the click count of a station by one.

        This should be called everytime when a user starts playing a stream to mark the stream more popular than others.
        Every call to this endpoint from the same IP address and for the same station only gets counted once per day.

        Parameters:
            station (Station, optional): The station to click.
            station_id (str, optional): The station uuid to click.
        """
        if (not station) and (not station_id):
            return
        if station:
            station_id = station.stationuuid
        url = await self.base_url / "json" / "url" / f"{station_id}"
        if self._disabled:
            return
        with contextlib.suppress(Exception):
            await self.request.get(url)
