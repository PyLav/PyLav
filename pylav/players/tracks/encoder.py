from __future__ import annotations

import asyncio
import struct
from typing import Any

from pylav.logging import getLogger
from pylav.utils.vendor.lavalink_py.datarw import DataWriter

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
    version: int = 3,
    **kwargs: Any,
) -> str:

    writer = DataWriter()
    writer.write_byte(struct.pack("B", version))
    writer.write_utf(title)
    writer.write_utf(author)
    writer.write_long(length)
    writer.write_utf(identifier)
    writer.write_boolean(isStream)
    writer.write_nullable_utf(uri)
    writer.write_utf(sourceName)
    writer.write_nullable_utf(artworkUrl)
    writer.write_nullable_utf(isrc)
    match sourceName:
        case "local" | "http" if probe is not None:
            writer.write_utf(probe)
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
        is_stream=is_stream,
        uri=uri,
        source=source,
        artworkUrl=artworkUrl,
        isrc=isrc,
        probe=probe,
        **kwargs,
    )
