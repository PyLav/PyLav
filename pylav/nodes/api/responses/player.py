from __future__ import annotations

import dataclasses


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class State:
    time: int = 0
    connected: bool = False
    ping: int = -1
    position: int | None = 0
