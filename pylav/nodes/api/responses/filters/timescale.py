from __future__ import annotations

import dataclasses
from typing import Annotated

from pylav.nodes.api.responses.filters.misc import ValueRange


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Timescale:
    speed: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None
    pitch: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None
    rate: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None

    def to_dict(self) -> dict[str, float]:
        response = {}
        if self.speed is not None:
            response["speed"] = self.speed
        if self.pitch is not None:
            response["pitch"] = self.pitch
        if self.rate is not None:
            response["rate"] = self.rate
        return response
