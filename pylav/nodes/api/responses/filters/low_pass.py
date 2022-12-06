from __future__ import annotations

import dataclasses
from typing import Annotated

from pylav.nodes.api.responses.filters.misc import ValueRange


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LowPass:
    smoothing: Annotated[float | None, ValueRange(min=1.0, max=float("inf"))] = None

    def to_dict(self) -> dict[str, float]:
        return {} if self.smoothing is None else {"smoothing": self.smoothing}
