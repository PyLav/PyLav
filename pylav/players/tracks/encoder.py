from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from pylav.constants.node import TRACK_VERSION
from pylav.logging import getLogger
from pylav.utils.vendor.lavalink_py.datarw import DataWriter

if TYPE_CHECKING:
    from pylav.nodes.node import Node

LOGGER = getLogger("PyLav.Track.Decoder")


# noinspection SpellCheckingInspection,PyPep8Naming
def encode_track(
    title: str,
    author: str,
    length: int,
    identifier: str,
    isStream: bool,
    uri: str | None,
    sourceName: str,
    artworkUrl: str | None = None,
    isrc: str | None = None,
    probe: str | None = None,
    version: int = TRACK_VERSION,
    **kwargs: Any,
) -> str:
    writer = DataWriter()
    writer.write_version(version)
    writer.write_utf(title)
    writer.write_utf(author)
    writer.write_long(length)
    writer.write_utf(identifier)
    writer.write_boolean(isStream)
    if version >= 2:
        writer.write_nullable_utf(uri)
    if version >= 3:
        writer.write_nullable_utf(artworkUrl)
        writer.write_nullable_utf(isrc)
    writer.write_utf(sourceName)
    match sourceName:
        case "local" | "http" if probe is not None:
            writer.write_utf(probe)
        case "spotify" | "applemusic" | "deezer" if version == 2:
            writer.write_nullable_utf(isrc)
            writer.write_nullable_utf(artworkUrl)
        case "yandexmusic" if version == 2:
            writer.write_nullable_utf(artworkUrl)
    writer.write_long(0)
    return writer.to_base64()


# noinspection SpellCheckingInspection,PyPep8Naming
async def async_encoder(
    title: str,
    author: str,
    length: int,
    identifier: str,
    is_stream: bool,
    uri: str | None,
    source: str,
    version: int = TRACK_VERSION,
    artworkUrl: str | None = None,
    isrc: str | None = None,
    probe: str | None = None,
    **kwargs: Any,
) -> str:
    return await asyncio.to_thread(
        encode_track,
        title=title,
        author=author,
        length=length,
        identifier=identifier,
        isStream=is_stream,
        uri=uri,
        sourceName=source,
        artworkUrl=artworkUrl,
        isrc=isrc,
        probe=probe,
        version=version,
        **kwargs,
    )


async def async_re_encoder(track: str, node: Node) -> str:
    track_obj = await node.fetch_decodetrack(track, raise_on_failure=True)
    track_data = track_obj.info.to_dict()
    return await async_encoder(**track_data)


async def async_bulk_re_encoder(track: list[str], node: Node) -> AsyncIterator[str]:
    track_objs = await node.post_decodetracks(track, raise_on_failure=True)
    for track_obj in track_objs:
        track_data = track_obj.info.to_dict()
        yield await async_encoder(**track_data)
