from __future__ import annotations

import dataclasses
from typing import NotRequired


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Info:
    name: str
    selectedTrack: int
    type: NotRequired[str] = "playlist"
    identifier: NotRequired[str | None] = None
    artworkUrl: NotRequired[str | None] = None
    author: NotRequired[str | None] = None
