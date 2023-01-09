"""
MIT License

Copyright (c) 2017-present Devoxin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import annotations

import struct
import typing
from base64 import b64decode, b64encode
from io import BytesIO


# noinspection SpellCheckingInspection
class DataReader:
    def __init__(self, ts: str) -> None:
        self._buf = BytesIO(b64decode(ts))
        # Added for PyLav
        self._flag_read = False
        self._flags = 0
        self._version_read = False
        self._version = 0

    def _read(self, count: int) -> bytes:
        return self._buf.read(count)

    def read_byte(self) -> bytes:
        return self._read(1)

    def read_boolean(self) -> bool:
        (result,) = struct.unpack("B", self.read_byte())
        return bool(result)

    def read_unsigned_short(self) -> int:
        (result,) = struct.unpack(">H", self._read(2))
        return typing.cast(int, result)

    def read_int(self) -> int:
        (result,) = struct.unpack(">i", self._read(4))
        return typing.cast(int, result)

    def read_long(self) -> int:
        (result,) = struct.unpack(">Q", self._read(8))
        return typing.cast(int, result)

    def read_utf(self) -> str:
        text_length = self.read_unsigned_short()
        return self._read(text_length).decode()

    def read_utfm(self) -> str:
        text_length = self.read_unsigned_short()
        utf_string = self._read(text_length)
        return self._read_utfm(text_length, utf_string)

    # Merged from utfm_codec.py
    @staticmethod
    def _read_utfm(utf_len: int, utf_bytes: bytes) -> str:
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
                    raise UnicodeError("Malformed input: partial character at end")
                char2 = utf_bytes[count - 1]
                if (char2 & 0xC0) != 0x80:
                    raise UnicodeError(f"Malformed input around byte {count}")

                char_shift = ((c & 0x1F) << 6) | (char2 & 0x3F)
                chars.append(chr(char_shift))
            elif shift == 14:
                count += 3
                if count > utf_len:
                    raise UnicodeError("Malformed input: partial character at end")

                char2 = utf_bytes[count - 2]
                char3 = utf_bytes[count - 1]

                if (char2 & 0xC0) != 0x80 or (char3 & 0xC0) != 0x80:
                    raise UnicodeError(f"Malformed input around byte {count - 1}")

                char_shift = ((c & 0x0F) << 12) | ((char2 & 0x3F) << 6) | ((char3 & 0x3F) << 0)
                chars.append(chr(char_shift))
            else:
                raise UnicodeError(f"malformed input around byte {count}")

        # noinspection SpellCheckingInspection
        return "".join(chars).encode("utf-16", "surrogatepass").decode("utf-16")

    # Added for PyLav
    def read_nullable_utf(self) -> str | None:
        return self.read_utf() if self.read_boolean() else None

    # Added for PyLav
    def read_nullable_utfm(self) -> str | None:
        return self.read_utfm() if self.read_boolean() else None

    # Added for PyLav
    def read_flags(self) -> int:
        if self._flag_read:
            return self._flags
        self._flags = (self.read_int() & 0xC0000000) >> 30
        self._flag_read = True
        return self._flags

    # Added for PyLav
    def read_version(self) -> int:
        if self._version_read:
            return self._version
        (version,) = (struct.unpack("B", self.read_byte())) if self.read_flags() & 1 != 0 else (1,)
        self._version = version
        self._version_read = True
        return self._version


class DataWriter:
    def __init__(self) -> None:
        self._buf = BytesIO()

    def _write(self, data: bytes) -> None:
        self._buf.write(data)

    def write_byte(self, byte: bytes) -> None:
        self._buf.write(byte)

    def write_boolean(self, boolean: bool) -> None:
        enc = struct.pack("B", 1 if boolean else 0)
        self.write_byte(enc)

    def write_unsigned_short(self, short: int) -> None:
        enc = struct.pack(">H", short)
        self._write(enc)

    def write_int(self, integer: int) -> None:
        enc = struct.pack(">i", integer)
        self._write(enc)

    def write_long(self, long_value: int) -> None:
        enc = struct.pack(">Q", long_value)
        self._write(enc)

    def write_utf(self, utf_string: str) -> None:
        utf = utf_string.encode("utf8")
        byte_len = len(utf)

        if byte_len > 65535:
            raise OverflowError("UTF string may not exceed 65535 bytes!")

        self.write_unsigned_short(byte_len)
        self._write(utf)

    def finish(self) -> bytes:
        with BytesIO() as track_buf:
            # Simplified for PyLav
            track_buf.write(self.get_flags())
            self._buf.seek(0)
            track_buf.write(self._buf.read())
            self._buf.close()
            track_buf.seek(0)
            return track_buf.read()

    # Added for PyLav
    def write_nullable_utf(self, utf_string: str | None) -> None:
        if utf_string is None:
            self.write_boolean(False)
        else:
            self.write_boolean(True)
            self.write_utf(utf_string)

    # Added for PyLav
    def write_version(self, version: int) -> None:
        self.write_byte(struct.pack("B", version))

    # Added for PyLav
    def get_flags(self) -> bytes:
        byte_len = self._buf.getbuffer().nbytes
        flags = byte_len | (1 << 30)
        return struct.pack(">i", flags)

    # Added for PyLav
    def to_base64(self) -> str:
        return b64encode(self.finish()).decode()
