from __future__ import annotations

import dataclasses
from typing import Annotated

from pylav.nodes.api.responses.filters.misc import ValueRange


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Rotation:
    rotationHz: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None

    def to_dict(self) -> dict[str, float]:
        if self.rotationHz is None:
            return {}
        return {"rotationHz": self.rotationHz}
