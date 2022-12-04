from __future__ import annotations

import dataclasses
from typing import Annotated

from pylav.nodes.api.responses.filters.misc import ValueRange


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Echo:
    delay: Annotated[int | None, ValueRange(min=0, max=float("inf"))] = None
    decay: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None

    def to_dict(self) -> dict[str, float | int]:
        response: dict[str, float | int] = {}
        if self.delay is not None:
            response["delay"] = self.delay
        if self.decay is not None:
            response["decay"] = self.decay
        return response
