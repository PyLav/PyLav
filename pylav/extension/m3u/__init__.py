from pylav.extension.m3u.base import load, loads


class M3UParser:
    __slots__ = ("_client",)

    def __init__(self, client: Client) -> None:
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    load = load
    loads = loads
