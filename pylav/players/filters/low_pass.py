from __future__ import annotations

from pylav.players.filters.misc import FilterMixin


class LowPass(FilterMixin):
    __slots__ = ("_smoothing", "_default")

    def __init__(self, smoothing: float | None = None) -> None:
        super().__init__()
        self.smoothing = smoothing

    def to_dict(self) -> dict[str, float | bool | None]:
        return {
            "smoothing": self.smoothing,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | bool | None]) -> LowPass:
        return cls(smoothing=data["smoothing"])

    def __repr__(self) -> str:
        return f"<LowPass: smoothing={self.smoothing}>"

    @property
    def smoothing(self) -> float | None:
        return self._smoothing

    @smoothing.setter
    def smoothing(self, v: float | None) -> None:
        self._smoothing = v

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
