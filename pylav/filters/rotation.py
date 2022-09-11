from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Rotation(FilterMixin):
    __slots__ = ("_hertz", "_off", "_default")

    def __init__(self, hertz: float = None):
        super().__init__()
        self.hertz = hertz
        self.off = hertz is None

    def to_dict(self) -> dict[str, float | bool | None]:
        return {
            "hertz": self.hertz,
            "off": self.off,
        }

    def to_json(self) -> dict[str, float | None]:
        return {
            "hertz": self.hertz,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | bool | None]) -> Rotation:
        c = cls(hertz=data["hertz"])
        c.off = data["off"]
        return c

    def __repr__(self):
        return f"<Rotation: hertz={self.hertz}>"

    @property
    def hertz(self) -> float | None:
        return self._hertz

    @hertz.setter
    def hertz(self, v: float | None):
        self._hertz = v
        self.off = v is None

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
        self.off = True
