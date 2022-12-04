from __future__ import annotations

import dataclasses
from typing import Annotated

from pylav.nodes.api.responses.filters.misc import ValueRange


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Karaoke:
    level: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    monoLevel: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    filterBand: float | None = None
    filterWidth: float | None = None

    def to_dict(self) -> dict[str, float]:
        response = {}
        if self.level is not None:
            response["level"] = self.level
        if self.monoLevel is not None:
            response["monoLevel"] = self.monoLevel
        if self.filterBand is not None:
            response["filterBand"] = self.filterBand
        if self.filterWidth is not None:
            response["filterWidth"] = self.filterWidth
        return response
