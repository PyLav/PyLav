from __future__ import annotations

import struct
from base64 import b64decode
from io import BytesIO


class DataReader:
    __slots__ = ("_buf",)

    def __init__(self, ts):
        self._buf = BytesIO(b64decode(ts))

    def _read(self, count):
        return self._buf.read(count)

    def read_byte(self) -> bytes:
        return self._read(1)

    def read_boolean(self) -> bool:
        (result,) = struct.unpack("B", self.read_byte())
        return result != 0

    def read_unsigned_short(self) -> int:
        (result,) = struct.unpack(">H", self._read(2))
        return result

    def read_int(self) -> int:
        (result,) = struct.unpack(">i", self._read(4))
        return result

    def read_long(self) -> int:
        (result,) = struct.unpack(">Q", self._read(8))
        return result

    def read_utf(self) -> bytes:
        text_length = self.read_unsigned_short()
        return self._read(text_length)

    def read_utfm(self) -> str:
        text_length = self.read_unsigned_short()
        utf_string = self._read(text_length)
        return read_utfm(text_length, utf_string)


def decode_track(track: str) -> tuple[dict[str, str | dict[str, str | bool | int | None]], int]:
    """Decodes a base64 track string into an Track object.

    Parameters
    ----------
    track: :class:`str`
        The base64 track string.

    Returns
    -------
    :class:`tuple` of :class:`dict` and :class:`int`
    The first element is a dictionary of track properties and the second element is encoding version.
    """
    reader = DataReader(track)

    flags = (reader.read_int() & 0xC0000000) >> 30
    version = struct.unpack("B", reader.read_byte()) if flags & 1 != 0 else 1

    title = reader.read_utfm()
    author = reader.read_utfm()
    length = reader.read_long()
    identifier = reader.read_utf().decode()
    is_stream = reader.read_boolean()
    uri = reader.read_utf().decode() if reader.read_boolean() else None
    source = reader.read_utf().decode()

    # Position
    _ = reader.read_long()

    track_object = {
        "track": track,
        "info": {
            "title": title,
            "author": author,
            "length": length,
            "identifier": identifier,
            "isStream": is_stream,
            "uri": uri,
            "isSeekable": not is_stream,
            "source": source,
        },
    }

    return track_object, version


def read_utfm(utf_len: int, utf_bytes: bytes) -> str:
    chars = []
    count = 0

    while count < utf_len:
        c = utf_bytes[count] & 0xFF
        if c > 127:
            break

        count += 1
        chars.append(chr(c))

    while count < utf_len:
        c = utf_bytes[count] & 0xFF
        shift = c >> 4

        if 0 <= shift <= 7:
            count += 1
            chars.append(chr(c))
        elif 12 <= shift <= 13:
            count += 2
            if count > utf_len:
                raise UnicodeError("malformed input: partial character at end")
            char2 = utf_bytes[count - 1]
            if (char2 & 0xC0) != 0x80:
                raise UnicodeError(f"malformed input around byte {count}")

            char_shift = ((c & 0x1F) << 6) | (char2 & 0x3F)
            chars.append(chr(char_shift))
        elif shift == 14:
            count += 3
            if count > utf_len:
                raise UnicodeError("malformed input: partial character at end")

            char2 = utf_bytes[count - 2]
            char3 = utf_bytes[count - 1]

            if (char2 & 0xC0) != 0x80 or (char3 & 0xC0) != 0x80:
                raise UnicodeError(f"malformed input around byte {str(count - 1)}")

            char_shift = ((c & 0x0F) << 12) | ((char2 & 0x3F) << 6) | ((char3 & 0x3F) << 0)
            chars.append(chr(char_shift))
        else:
            raise UnicodeError(f"malformed input around byte {count}")

    return "".join(chars).encode("utf-16", "surrogatepass").decode("utf-16")
