from __future__ import annotations

import dataclasses
from typing import NotRequired


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Info:
    name: str
    selectedTrack: int
    type: NotRequired[str] = "playlist"
    url: NotRequired[str | None] = None
    artworkUrl: NotRequired[str | None] = None
    author: NotRequired[str | None] = None

    def to_dict(self) -> JSON_DICT_TYPE:
        return dataclasses.asdict(self)
