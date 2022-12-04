from __future__ import annotations

import dataclasses


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Info:
    identifier: str
    isSeekable: bool
    author: str
    length: int = 0
    isStream: bool = False
    position: int | None = 0
    title: str = ""
    uri: str | None = None
    sourceName: str | None = None
    thumbnail: str | None = None
    isrc: str | None = None
    probeInfo: str | None = None

    def to_dict(self) -> dict[str, str | int | bool | None]:
        return dataclasses.asdict(self)

    def to_database(self) -> dict[str, str | int | bool | None]:
        return {
            "identifier": self.identifier,
            "title": self.title,
            "uri": self.uri,
            "sourceName": self.sourceName,
            "isrc": self.isrc,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Track:
    info: Info | dict
    encoded: str | None = None
    track: str | None = None

    def __post_init__(self) -> None:
        if self.encoded is None:
            object.__setattr__(self, "encoded", self.track)
        if isinstance(self.info, dict):
            object.__setattr__(self, "info", Info(**self.info))

    def to_dict(self) -> dict[str, str | int | bool | None | dict[str, str | int | bool | None]]:
        return {
            "info": dataclasses.asdict(self.info),
            "encoded": self.encoded,
            "track": self.track,
        }
