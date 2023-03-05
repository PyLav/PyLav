from __future__ import annotations

import dataclasses

from pylav.type_hints.dict_typing import JSON_DICT_TYPE


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class State:
    time: int
    connected: bool
    ping: int
    position: int | None = 0

    def to_dict(self) -> JSON_DICT_TYPE:
        return {
            "time": self.time,
            "connected": self.connected,
            "ping": self.ping,
            "position": self.position,
        }

    def __repr__(self) -> str:
        return f"<State(time={self.time} position={self.position} connected={self.connected} ping={self.ping})"
