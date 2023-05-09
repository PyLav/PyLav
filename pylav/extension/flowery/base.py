from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import aiohttp
import aiohttp_client_cache

from pylav.compat import json
from pylav.constants.config import REDIS_FULL_ADDRESS_RESPONSE_CACHE
from pylav.extension.flowery.lyrics import LyricsAPI
from pylav.utils.aiohttp_postgres_cache import PostgresCacheBackend

if TYPE_CHECKING:
    from pylav.core.client import Client


class FloweryAPI:
    """A wrapper for the Flowery API."""

    def __init__(self, client: Client) -> None:
        if REDIS_FULL_ADDRESS_RESPONSE_CACHE:
            self._aiohttp_client_cache = aiohttp_client_cache.RedisBackend(
                address=REDIS_FULL_ADDRESS_RESPONSE_CACHE,
                cache_control=True,
                allowed_codes=(200,),
                allowed_methods=("GET",),
                include_headers=True,
                expire_after=datetime.timedelta(days=1),
                timeout=2.5,
            )
        else:
            self._aiohttp_client_cache = PostgresCacheBackend(
                cache_control=True,
                allowed_codes=(200,),
                allowed_methods=("GET",),
                include_headers=True,
                expire_after=datetime.timedelta(days=1),
                timeout=2.5,
            )
        self._cached_session = aiohttp_client_cache.CachedSession(
            timeout=aiohttp.ClientTimeout(total=30),
            json_serialize=json.dumps,
            cache=self._aiohttp_client_cache,
            headers={"User-Agent": f"PyLav/{client.lib_version} (https://github.com/PyLav/PyLav)"},
        )

        self._lyrics = LyricsAPI(client, self)

    async def shutdown(self) -> None:
        """Close the cached session."""
        await self._cached_session.close()

    @property
    def lyrics(self) -> LyricsAPI:
        """The lyrics API client."""
        return self._lyrics
