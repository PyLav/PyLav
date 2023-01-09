from __future__ import annotations

import asyncio
import typing

from dacite import from_dict  # type: ignore

from pylav.logging import getLogger
from pylav.nodes.api.responses.track import Track
from pylav.utils.vendor.lavalink_py.datarw import DataReader

LOGGER = getLogger("PyLav.Track.Decoder")


# noinspection SpellCheckingInspection,PyPep8Naming
def decode_track(track: str) -> Track:
    """Decodes a base64 track string into a Track object.

    Parameters
    ----------
    track: :class:`str`
        The base64 track string.

    Returns
    -------
    :class:`Track`
    The decoded Track object
    """
    reader = DataReader(track)
    version = reader.read_version()
    plugin_info = {}
    title = reader.read_utfm()
    author = reader.read_utfm()
    length = reader.read_long()
    identifier = reader.read_utf()
    is_stream = reader.read_boolean()
    uri = reader.read_nullable_utf() if version >= 2 else None
    if version >= 3:
        artworkUrl = reader.read_nullable_utf()
        isrc = reader.read_nullable_utf()
    else:
        artworkUrl = None
        isrc = None
    source = reader.read_utf()
    try:
        match source:
            case "local" | "http" if version >= 2:
                plugin_info["probeInfo"] = reader.read_utfm()
            case "spotify" | "applemusic" | "deezer" if version == 2:
                isrc = reader.read_nullable_utf()
                artworkUrl = reader.read_nullable_utf()
            case "yandexmusic" if version == 2:
                artworkUrl = reader.read_nullable_utf()
        # Position
        __ = reader.read_long()  # Discard position, we don't need it
    except Exception as exc:
        LOGGER.verbose("Error while decoding version %d track: %s", version, track, exc_info=exc)
        raise UnicodeError("Error while decoding track") from exc

    return typing.cast(
        Track,
        from_dict(
            data_class=Track,
            data={
                "encoded": track,
                "info": {
                    "version": version,
                    "title": title,
                    "author": author,
                    "length": length,
                    "identifier": identifier,
                    "isStream": is_stream,
                    "uri": uri,
                    "isSeekable": not is_stream,
                    "sourceName": source,
                    "artworkUrl": artworkUrl,
                    "isrc": isrc,
                    "position": 0,
                },
                "pluginInfo": plugin_info,
            },
        ),
    )


async def async_decoder(track: str) -> Track:
    return await asyncio.to_thread(decode_track, track=track)
