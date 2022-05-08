from __future__ import annotations

from pylav.filters.utils import FilterMixin


class LowPass(FilterMixin):
    def __init__(self, smoothing: float):
        self._smoothing = smoothing
        self.off = False

    def to_dict(self) -> dict:
        return {
            "smoothing": self.smoothing,
            "off": self.off,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LowPass:
        c = cls(
            smoothing=data["smoothing"],
        )
        c.off = data["off"]
        return c

    def __repr__(self):
        return f"<LowPass: smoothing={self.smoothing}>"

    @property
    def smoothing(self) -> float:
        return self._smoothing

    @smoothing.setter
    def smoothing(self, v: float):
        self._smoothing = v
        self.off = False

    @classmethod
    def default(cls) -> LowPass:
        c = cls(smoothing=20.0)
        c.off = True
        return c

    def get(self) -> dict[str, float]:
        return (
            {}
            if self.off
            else {
                "smoothing": self.smoothing,
            }
        )

    def reset(self) -> None:
        self.smoothing = 20.0
        self.off = True
