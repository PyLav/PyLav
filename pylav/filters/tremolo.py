from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Tremolo(FilterMixin):
    def __init__(self, frequency: float, depth: float):
        self.frequency = frequency
        self.depth = depth
        self.off = False

    def to_dict(self) -> dict:
        return {
            "frequency": self.frequency,
            "depth": self.depth,
            "off": self.off,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Tremolo:
        c = cls(frequency=data["frequency"], depth=data["depth"])
        c.off = data["off"]
        return c

    def __repr__(self):
        return f"<Tremolo: frequency={self.frequency}, depth={self.depth}>"

    @property
    def frequency(self) -> float:
        return self._frequency

    @frequency.setter
    def frequency(self, v: float):
        if v <= 0:
            raise ValueError(f"Frequency must be must be greater than 0, not {v}")
        self._frequency = v
        self.off = False

    @property
    def depth(self) -> float:
        return self._depth

    @depth.setter
    def depth(self, v: float):
        if not (0.0 < v <= 1.0):
            raise ValueError(f"Depth must be must be 0.0 < x ≤ 1.0, not {v}")
        self._depth = v
        self.off = False

    @classmethod
    def default(cls) -> Tremolo:
        c = cls(frequency=2.0, depth=0.5)
        c.off = True
        return c

    def get(self) -> dict[str, float]:
        return (
            {}
            if self.off
            else {
                "frequency": self.frequency,
                "depth": self.depth,
            }
        )

    def reset(self) -> None:
        self.frequency = 2.0
        self.depth = 0.5
        self.off = True
