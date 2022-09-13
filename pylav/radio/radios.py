from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

import aiohttp
import aiohttp_client_cache
import ujson

from pylav._logging import getLogger
from pylav.radio.base_url import pick_base_url
from pylav.radio.objects import Codec, Country, CountryCode, Language, State, Station, Tag
from pylav.radio.utils import type_check
from pylav.utils import AsyncIter

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("PyLav.RadioBrowser")


class Request:
    __slots__ = ("_headers", "_session")

    def __init__(self, headers: dict[str, str] = None, session: aiohttp_client_cache.CachedSession = None):
        self._headers = headers
        self._session = session

    async def get(self, url: str, skip_cache: bool = False, **kwargs: Any):
        if not skip_cache:
            async with self._session.get(url, headers=self._headers, params=kwargs) as resp:
                if resp.status == 200:
                    return await resp.json(loads=ujson.loads)
        else:
            async with aiohttp_client_cache.CachedSession(
                headers=self._headers, timeout=aiohttp.ClientTimeout(total=30), json_serialize=ujson.dumps
            ) as session:
                async with session.get(url, params=kwargs) as resp:
                    if resp.status == 200:
                        return await resp.json(loads=ujson.loads)
        return resp.raise_for_status()


class RadioBrowser:
    """This class implements the main interface for the Radio Browser API."""

    def __init__(self, client: Client):
        headers = {"User-Agent": f"PyLav/{client.lib_version}"}
        self._lib_client = client
        self.client = Request(headers=headers, session=self._lib_client.cached_session)
        self._disabled = False

    async def initialize(self) -> None:
        try:
            self._disabled = not await self.base_url
            if self._disabled:
                LOGGER.error("Error while initializing the Radio Browser extension - disabling it")
                return
        except Exception as e:
            LOGGER.error("Error while initializing the Radio Browser extension - disabling it")
            LOGGER.debug(e, exc_info=e)
            self._disabled = True
        else:
            LOGGER.debug("Priming the cache")
            asyncio.ensure_future(
                asyncio.gather(
                    self.countries(),
                    self.countrycodes(),
                    self.codecs(),
                    self.states(),
                    self.languages(),
                    self.tags(),
                    self.stations(),
                    self.stations_by_clicks(limit=25),
                    self.stations_by_votes(limit=25),
                )
            )
            LOGGER.debug("Cache primed")

    @property
    async def base_url(self) -> str | None:
        return await pick_base_url(self._lib_client.session)

    async def build_url(self, endpoint: str) -> str | None:
        if url := await self.base_url:
            return f"{url}/{endpoint}"
        self._disabled = True

    @property
    def disabled(self) -> bool:
        return self._disabled

    @type_check
    async def countries(self, code: str = None) -> list[Country]:
        """Lists all countries.

        Args:
            code (str, optional): Filter by country code. Defaults to None.

        Returns:
            list: Countries.

        See details:
            https://de1.api.radio-browser.info/#List_of_countries
        """
        endpoint = f"json/countries/{code}" if code else "json/countries/"
        url = await self.build_url(endpoint)
        if self._disabled:
            return []
        return [Country(**country) async for country in AsyncIter(await self.client.get(url, hidebroken="true"))]

    @type_check
    async def countrycodes(self, code: str = None) -> list[CountryCode]:
        """Lists all countries.

        Args:
            code (str, optional): Filter by country code. Defaults to None.

        Returns:
            list: Countries.

        See details:
            https://de1.api.radio-browser.info/#List_of_countrycodes
        """
        endpoint = f"json/countrycodes/{code}" if code else "json/countrycodes/"
        url = await self.build_url(endpoint)
        if self._disabled:
            return []
        return [CountryCode(**country) async for country in AsyncIter(await self.client.get(url, hidebroken="true"))]

    @type_check
    async def codecs(self, codec: str = None) -> list[Codec]:
        """Lists all codecs.

        Args:
            codec (str, optional): Filter by codec. Defaults to None.

        Returns:
            list: Codecs.

        See details:
            https://de1.api.radio-browser.info/#List_of_codecs
        """
        endpoint = "json/codecs/"
        url = await self.build_url(endpoint)
        if self._disabled:
            return []
        response = await self.client.get(url, hidebroken="true")
        if codec:
            return [
                Codec(**tag) async for tag in AsyncIter(response).filter(lambda s: s["name"].lower() == codec.lower())
            ]
        return [Codec(**tag) async for tag in AsyncIter(response)]

    @type_check
    async def states(self, country: str = None, state: str = None) -> list[State]:
        """Lists all states.

        Args:
            country (str, optional): Filter by country. Defaults to None.
            state (str, optionla): Filter by state.  Defaults to None.

        Returns:
            list: States.

        See details:
            https://de1.api.radio-browser.info/#List_of_states
        """
        endpoint = "json/states"
        url = await self.build_url(endpoint)
        if self._disabled:
            return []
        response = await self.client.get(url, hidebroken="true")

        if country:
            if state:
                return [
                    State(**state)
                    async for state in AsyncIter(response).filter(
                        lambda s: s["country"].lower() == country.lower() and s["name"].lower() == state.lower()
                    )
                ]
            return [
                State(**state)
                async for state in AsyncIter(response).filter(lambda s: s["country"].lower() == country.lower())
            ]
        if state:
            return [
                State(**state)
                async for state in AsyncIter(response).filter(lambda s: s["name"].lower() == state.lower())
            ]
        return [State(**state) async for state in AsyncIter(response)]

    @type_check
    async def languages(self, language: str = None) -> list[Language]:
        """Lists all languages.

        Args:
            language (str, optional): Filter by language. Defaults to None.

        Returns:
            list: Languages.

        See details:
            https://de1.api.radio-browser.info/#List_of_languages
        """
        endpoint = f"json/languages/{language}" if language else "json/languages/"
        url = await self.build_url(endpoint)
        if self._disabled:
            return []
        response = await self.client.get(url, hidebroken="true")
        return [Language(**language) async for language in AsyncIter(response)]

    @type_check
    async def tags(self, tag: str = None) -> list[Tag]:
        """Lists all tags.

        Args:
            tag (str, optional): Filter by tag. Defaults to None.

        Returns:
            list: Tags.

        See details:
            https://de1.api.radio-browser.info/#List_of_tags
        """
        if tag:
            tag = tag.lower()
            endpoint = f"json/tags/{tag}"
        else:
            endpoint = "json/tags/"
        url = await self.build_url(endpoint)
        if self._disabled:
            return []
        response = await self.client.get(url, hidebroken="true")
        return [Tag(**tag) async for tag in AsyncIter(response)]

    async def station_by_uuid(self, stationuuid: str) -> list[Station]:
        """Radio station by stationuuid.

        Args:
            stationuuid (str): A globally unique identifier for the station.

        Returns:
            list: Stations.

        See details:
            https://de1.api.radio-browser.info/#List_of_radio_stations
        """
        endpoint = f"json/stations/byuuid/{stationuuid}"
        url = await self.build_url(endpoint)
        if self._disabled:
            return []
        response = await self.client.get(url, hidebroken="true")
        return [Station(radio_api_client=self, **station) async for station in AsyncIter(response)]

    async def stations_by_name(
        self, name: str, exact: bool = False, **kwargs: str | int | bool | None
    ) -> list[Station]:
        """Lists all radio stations by name.

        Args:
            name (str): The name of the station.
            reverse (bool): Reverse the result list if set to True.

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

        Args:
            code (str): Official countrycodes as in ISO 3166-1 alpha-2.

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

    async def click_counter(self, stationuuid: str) -> dict[str, str | int | bool]:
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
        endpoint = f"json/url/{stationuuid}"
        url = await self.build_url(endpoint)
        return [] if self._disabled else await self.client.get(url, hidebroken="true")

    async def stations(self, **kwargs: str | int | bool | None) -> list[Station]:
        """Lists all radio stations.

        Returns:
            list: Stations.

        See details:
            https://nl1.api.radio-browser.info/#List_of_all_radio_stations
        """
        endpoint = "json/stations"
        kwargs["hidebroken"] = kwargs.pop("hidebroken", "true")
        url = await self.build_url(endpoint)
        if self._disabled:
            return []
        return [
            Station(radio_api_client=self, **station)
            async for station in AsyncIter(await self.client.get(url, **kwargs))
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
        if self._disabled:
            return []
        endpoint = f"json/stations/topvote/{limit}"
        url = await self.build_url(endpoint)
        if self._disabled:
            return []
        kwargs["hidebroken"] = kwargs.pop("hidebroken", "true")
        response = await self.client.get(url, **kwargs)
        return [Station(radio_api_client=self, **station) async for station in AsyncIter(response)]

    async def stations_by_clicks(self, limit: int, **kwargs: str | int | bool | None) -> list[Station]:
        """A list of the stations that are clicked the most.

        Args:
            limit: Number of wanted stations

        Returns:
            list: Stations.

        See details:
            https://nl1.api.radio-browser.info/#Stations_by_clicks
        """
        endpoint = f"json/stations/topclick/{limit}"
        url = await self.build_url(endpoint)
        if self._disabled:
            return []
        kwargs["hidebroken"] = kwargs.pop("hidebroken", "true")
        response = await self.client.get(url, **kwargs)
        return [Station(radio_api_client=self, **station) async for station in AsyncIter(response)]

    @type_check
    async def search(self, **kwargs: str | int | bool | None) -> list[Station]:
        """Advanced search.

        It will search for the station whose attribute
        contains the search term.

        Args:
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
        endpoint = "json/stations/search"
        # lowercase tag reference since the API turned to be case-sensitive
        for paramkey in ["tag", "tagList"]:
            if paramkey in kwargs:
                kwargs[paramkey] = kwargs[paramkey].lower()
        kwargs["hidebroken"] = kwargs.pop("hidebroken", "true")
        if kwargs["hidebroken"] is False:
            kwargs["hidebroken"] = "false"
        url = await self.build_url(endpoint)
        if self._disabled:
            return []
        return [
            Station(radio_api_client=self, **station)
            async for station in AsyncIter(await self.client.get(url, **kwargs))
        ]

    async def click(self, station: Station = None, station_id: str = None) -> None:
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
        endpoint = f"json/url/{station_id}"
        url = await self.build_url(endpoint)
        if self._disabled:
            return
        with contextlib.suppress(Exception):
            await self.client.get(url)
