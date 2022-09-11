from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Tremolo(FilterMixin):
    __slots__ = ("_frequency", "_depth", "_off", "_default")

    def __init__(self, frequency: float = None, depth: float = None):
        super().__init__()
        self.frequency = frequency
        self.depth = depth
        self.off = all(v is None for v in [frequency, depth])

    def to_dict(self) -> dict[str, float | bool | None]:
        return {
            "frequency": self.frequency,
            "depth": self.depth,
            "off": self.off,
        }

    def to_json(self) -> dict[str, float | None]:
        return {
            "frequency": self.frequency,
            "depth": self.depth,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | bool | None]) -> Tremolo:
        c = cls(frequency=data["frequency"], depth=data["depth"])
        c.off = data["off"]
        return c

    def __repr__(self):
        return f"<Tremolo: frequency={self.frequency}, depth={self.depth}>"

    @property
    def frequency(self) -> float | None:
        return self._frequency

    @frequency.setter
    def frequency(self, v: float | None):
        if v is None:
            self._frequency = v
            self.off = all(
                v is None
                for v in [getattr(self, attr, None) for attr in self.__slots__ if attr not in {"_off", "_default"}]
            )
            return
        if v <= 0:
            raise ValueError(f"Frequency must be must be greater than 0, not {v}")
        self._frequency = v
        self.off = False

    @property
    def depth(self) -> float:
        return self._depth

    @depth.setter
    def depth(self, v: float):
        if v is None:
            self._depth = v
            self.off = all(
                v is None
                for v in [getattr(self, attr, None) for attr in self.__slots__ if attr not in {"_off", "_default"}]
            )
            return
        if not (0.0 < v <= 1.0):
            raise ValueError(f"Depth must be must be 0.0 < x ≤ 1.0, not {v}")
        self._depth = v
        self.off = False

    @classmethod
    def default(cls) -> Tremolo:
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
        self.off = True
