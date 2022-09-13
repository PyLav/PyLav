from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Volume(FilterMixin):
    __slots__ = ("_value", "_default")

    def __init__(self, value: int | float | Volume):
        super().__init__()
        if isinstance(value, Volume):
            self.value = value.value
        elif isinstance(value, int):
            self.value = value / 100
        else:
            self.value = value

    def to_dict(self) -> dict[str, float | bool]:
        return {"volume": self.value}

    @classmethod
    def from_dict(cls, data: dict[str, float | bool]) -> Volume:
        return cls(data["volume"])

    def __float__(self):
        return self.value

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float):
        if v < 0:
            raise ValueError(f"Volume must be must be greater than or equals to zero, not {v}")
        v = float(round(v, 2))
        self._value = v

    @classmethod
    def default(cls) -> Volume:
        return cls(value=1.0)

    def increase(self, by: float = 0.05) -> None:
        self.value += by

    def decrease(self, by: float = 0.05) -> None:
        self.value -= by

    def reset(self) -> None:
        self.value = 1.0

    def get(self) -> float:
        return self.value

    def get_int_value(self) -> int:
        return min(max(int(round(self.value * 100)), 0), 1000)

    def __repr__(self):
        return str(self.value)
