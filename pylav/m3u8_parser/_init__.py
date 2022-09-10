from __future__ import annotations

import asyncio
import os

from aiocache import Cache, cached

from pylav.m3u8_parser.httpclient import DefaultHTTPClient, _parsed_url
from pylav.m3u8_parser.model import (
    M3U8,
    ContentSteering,
    DateRange,
    DateRangeList,
    IFramePlaylist,
    Key,
    Media,
    MediaList,
    PartialSegment,
    PartialSegmentList,
    PartInformation,
    Playlist,
    PlaylistList,
    PreloadHint,
    RenditionReport,
    RenditionReportList,
    Segment,
    SegmentList,
    ServerControl,
    Skip,
    Start,
)
from pylav.m3u8_parser.parser import ParseError, is_url, parse
from pylav.vendored import aiopath

# coding: utf-8
# Copyright 2014 Globo.com Player authors. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.


__all__ = (
    "M3U8",
    "Segment",
    "SegmentList",
    "PartialSegment",
    "PartialSegmentList",
    "Key",
    "Playlist",
    "IFramePlaylist",
    "Media",
    "MediaList",
    "PlaylistList",
    "Start",
    "RenditionReport",
    "RenditionReportList",
    "ServerControl",
    "Skip",
    "PartInformation",
    "PreloadHint",
    "DateRange",
    "DateRangeList",
    "ContentSteering",
    "loads",
    "load",
    "parse",
    "ParseError",
)


@cached(ttl=600, cache=Cache.MEMORY, namespace="m3u8_loads")
async def loads(self, content: str, uri: str = None, custom_tags_parser=None):
    """
    Given a string with a m3u8 content, returns a M3U8 object.
    Optionally parses a uri to set a correct base_uri on the M3U8 object.
    Raises ValueError if invalid content
    """

    if uri is None:
        return await asyncio.to_thread(M3U8, content, custom_tags_parser=custom_tags_parser)
    else:
        _parsed_url(uri)


@cached(ttl=600, cache=Cache.MEMORY, namespace="m3u8_load")
async def load(
    self,
    uri: str,
    timeout: float = None,
    headers: dict = None,
    custom_tags_parser=None,
    http_client: type[DefaultHTTPClient] = DefaultHTTPClient(),  # type: ignore
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
        return await _load_from_file(uri, custom_tags_parser)


async def _load_from_file(uri: str, custom_tags_parser=None):
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
