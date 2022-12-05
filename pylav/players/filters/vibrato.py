from __future__ import annotations

from pylav.players.filters.misc import FilterMixin


class Vibrato(FilterMixin):
    __slots__ = ("_frequency", "_depth", "_default")

    def __init__(self, frequency: float | None = None, depth: float | None = None) -> None:
        super().__init__()
        self.frequency = frequency
        self.depth = depth

    def to_dict(self) -> dict[str, float | bool | None]:
        return {
            "frequency": self.frequency,
            "depth": self.depth,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | bool | None]) -> Vibrato:
        return cls(frequency=data["frequency"], depth=data["depth"])

    def __repr__(self) -> str:
        return f"<Vibrato: frequency={self.frequency}, depth={self.depth}>"

    @property
    def frequency(self) -> float | None:
        return self._frequency

    @frequency.setter
    def frequency(self, v: float | None) -> None:
        if v is None or v == 0:
            self._frequency = v
            return
        if not (0.0 < v <= 14.0):
            raise ValueError(f"Frequency must be must be 0.0 < v <= 14.0, not {v}")
        self._frequency = v

    @property
    def depth(self) -> float | None:
        return self._depth

    @depth.setter
    def depth(self, v: float | None) -> None:
        if v is None:
            self._depth = v
            return
        if not (0.0 < v <= 1.0):
            raise ValueError(f"Depth must be must be 0.0 < x ≤ 1.0, not {v}")
        self._depth = v

    @classmethod
    def default(cls) -> Vibrato:
        return cls()

    def get(self) -> dict[str, float]:
        if self.off:
            return {}
        response = {}
        if self.frequency is not None:
            response["frequency"] = self.frequency
        if self.depth is not None:
            response["depth"] = self.depth
        return response

    def reset(self) -> None:
        self.frequency = self.depth = None
