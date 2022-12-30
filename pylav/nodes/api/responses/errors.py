from __future__ import annotations

import dataclasses
from datetime import datetime


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkError:
    timestamp: int | datetime
    status: int
    error: str
    message: str
    path: str
    trace: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.timestamp, int):
            object.__setattr__(self, "timestamp", datetime.fromtimestamp(self.timestamp / 1000))

    def __bool__(self) -> bool:
        return False
