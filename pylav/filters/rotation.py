from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Rotation(FilterMixin):
    __slots__ = ("_hertz", "_default")

    def __init__(self, hertz: float = None):
        super().__init__()
        self.hertz = hertz

    def to_dict(self) -> dict[str, float | bool | None]:
        return {
            "hertz": self.hertz,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | bool | None]) -> Rotation:
        return cls(hertz=data["hertz"])

    def __repr__(self):
        return f"<Rotation: hertz={self.hertz}>"

    @property
    def hertz(self) -> float | None:
        return self._hertz

    @hertz.setter
    def hertz(self, v: float | None):
        self._hertz = v

    @classmethod
    def default(cls) -> Rotation:
        return cls()

    def get(self) -> dict[str, float]:
        if self.off:
            return {}
        response = {}
        if self.hertz is not None:
            response["rotationHz"] = self.hertz
        return response

    def reset(self) -> None:
        self.hertz = None
