from __future__ import annotations

import dataclasses


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class State:
    time: int
    connected: bool
    ping: int
    position: int | None = 0
