from __future__ import annotations

import dataclasses


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Info:
    name: str
    selectedTrack: int
