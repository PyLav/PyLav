from __future__ import annotations

import dataclasses


@dataclasses.dataclass(repr=True, frozen=True, slots=True)
class ValueRange:
    min: float
    max: float

    def validate_value(self, x: float) -> None:
        if not (self.min <= x <= self.max):
            raise ValueError(f"{x} must be in range({self.min}, {self.max})")
