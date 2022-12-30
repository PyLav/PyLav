from __future__ import annotations

from typing import TYPE_CHECKING

from pylav.extension.m3u.base import load, loads

if TYPE_CHECKING:
    from pylav.core.client import Client


class M3UParser:
    __slots__ = ("_client",)

    def __init__(self, client: Client) -> None:
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    load = load
    loads = loads
