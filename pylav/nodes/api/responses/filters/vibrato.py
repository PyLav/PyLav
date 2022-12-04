from __future__ import annotations

import dataclasses
from typing import Annotated

from pylav.nodes.api.responses.filters.misc import ValueRange


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Vibrato:
    frequency: Annotated[float | None, ValueRange(min=0, max=14)] = None
    depth: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None

    def to_dict(self) -> dict[str, float]:
        response = {}
        if self.frequency is not None:
            response["frequency"] = self.frequency
        if self.depth is not None:
            response["depth"] = self.depth
        return response
