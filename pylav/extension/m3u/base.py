from __future__ import annotations

import asyncio
import os

import aiopath
from cashews import Cache

from pylav.extension.m3u.http_client import DefaultHTTPClient, parsed_url
from pylav.extension.m3u.models import M3U8
from pylav.extension.m3u.parser import is_url

# coding: utf-8
# Copyright 2014 Globo.com Player authors. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.


CACHE = Cache("M3U3CACHE")
CACHE.setup("mem://?check_interval=10", size=1_000_000, enable=True)


@CACHE(ttl=600, prefix="m3u_loads")
async def loads(self, content: str, uri: str = None, custom_tags_parser=None):  # noqa
    """
    Given a string with a m3u8 content, returns a M3U8 object.
    Optionally parses a uri to set a correct base_uri on the M3U8 object.
    Raises ValueError if invalid content
    """

    if uri is None:
        return await asyncio.to_thread(M3U8, content, custom_tags_parser=custom_tags_parser)
    else:
        parsed_url(uri)


@CACHE(ttl=600, prefix="m3u_load")
async def load(
    self,  # noqa
    uri: str,
    timeout: float = None,
    headers: dict[str, str] = None,
    custom_tags_parser=None,
    http_client: DefaultHTTPClient = DefaultHTTPClient(),
    verify_ssl: bool = True,
):
    """
    Retrieves the content from a given URI and returns a M3U8 object.
    Raises ValueError if invalid content or IOError if request fails.
    """
    if headers is None:
        headers = {}
    if is_url(uri):
        content, base_uri = await http_client.download(uri=uri, timeout=timeout, headers=headers, verify_ssl=verify_ssl)
        return await asyncio.to_thread(M3U8, content, base_uri=base_uri, custom_tags_parser=custom_tags_parser)
    else:
        return await load_from_file(uri, custom_tags_parser)


async def load_from_file(uri: str, custom_tags_parser=None):
    """Loads a m3u8 file from the filesystem

    Parameters:
    -----------
    uri: str
        uri of the m3u8 file
    custom_tags_parser: callable
        custom tags parser function
    """

    path = aiopath.AsyncPath(uri)
    async with path.open("r", encoding="utf8") as file:
        raw_content = (await file.read()).strip()
    base_uri = os.path.dirname(uri)
    return M3U8(raw_content, base_uri=base_uri, custom_tags_parser=custom_tags_parser)
