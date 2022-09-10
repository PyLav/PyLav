from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pylav.client import Client

from pylav.m3u8_parser._init__ import load, loads


class M3U8Parser:
    __slots__ = ("_client",)

    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    load = load
    loads = loads
