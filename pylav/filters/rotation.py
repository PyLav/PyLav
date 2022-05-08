from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Rotation(FilterMixin):
    def __init__(self, hertz: float):
        self.hertz = hertz
        self.off = False

    def to_dict(self) -> dict:
        return {
            "hertz": self.hertz,
            "off": self.off,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Rotation:
        c = cls(hertz=data["hertz"])
        c.off = data["off"]
        return c

    def __repr__(self):
        return f"<Rotation: hertz={self.hertz}>"

    @property
    def hertz(self) -> float:
        return self._hertz

    @hertz.setter
    def hertz(self, v: float):
        self._hertz = v
        self.off = False

    @classmethod
    def default(cls) -> Rotation:
        c = cls(hertz=0.0)
        c.off = True
        return c

    def get(self) -> dict[str, float]:
        return (
            {}
            if self.off
            else {
                "rotationHz": self.hertz,
            }
        )

    def reset(self) -> None:
        self.hertz = 0.0
        self.off = True
