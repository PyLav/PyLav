from __future__ import annotations

from pylav.filters.utils import FilterMixin


class LowPass(FilterMixin):
    __slots__ = ("_smoothing", "_off", "_default")

    def __init__(self, smoothing: float = None):
        super().__init__()
        self.smoothing = smoothing
        self.off = smoothing is None

    def to_dict(self) -> dict[str, float | bool | None]:
        return {
            "smoothing": self.smoothing,
            "off": self.off,
        }

    def to_json(self) -> dict[str, float | None]:
        return {
            "smoothing": self.smoothing,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | bool | None]) -> LowPass:
        c = cls(
            smoothing=data["smoothing"],
        )
        c.off = data["off"]
        return c

    def __repr__(self):
        return f"<LowPass: smoothing={self.smoothing}>"

    @property
    def smoothing(self) -> float | None:
        return self._smoothing

    @smoothing.setter
    def smoothing(self, v: float | None):
        self._smoothing = v
        self.off = v is None

    @classmethod
    def default(cls) -> LowPass:
        return cls()

    def get(self) -> dict[str, float]:
        if self.off:
            return {}
        response = {}
        if self.smoothing is not None:
            response["smoothing"] = self.smoothing
        return response

    def reset(self) -> None:
        self.smoothing = None
        self.off = True
