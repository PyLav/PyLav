import asyncio

from pylav.logging import getLogger
from pylav.utils.vendored.lavalink_py.datarw import DataWriter

LOGGER = getLogger("PyLav.Track.Decoder")


def encode_track(
    title: str,
    author: str,
    length: int,
    identifier: str,
    is_stream: bool,
    uri: str | None,
    source: str,
    thumbnail: str | None = None,
    isrc: str | None = None,
    probe: str | None = None,
) -> str:

    writer = DataWriter()
    writer.write_utf(title)
    writer.write_utf(author)
    writer.write_long(length)
    writer.write_utf(identifier)
    writer.write_boolean(is_stream)
    writer.write_nullable_utf(uri)
    writer.write_utf(source)

    match source:
        case "deezer" | "spotify" | "applemusic":
            writer.write_nullable_utf(isrc)
            writer.write_nullable_utf(thumbnail)
        case "yandexmusic":
            writer.write_nullable_utf(thumbnail)
        case "local" | "http" if probe is not None:
            writer.write_utf(probe)
    writer.write_long(0)
    return writer.to_base64()


async def async_encoder(
    title: str,
    author: str,
    length: int,
    identifier: str,
    is_stream: bool,
    uri: str | None,
    source: str,
    thumbnail: str | None = None,
    isrc: str | None = None,
    probe: str | None = None,
) -> str:

    return await asyncio.to_thread(
        encode_track, title, author, length, identifier, is_stream, uri, source, thumbnail, isrc, probe
    )
