from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Karaoke(FilterMixin):
    __slots__ = ("_level", "_mono_level", "_filter_band", "_filter_width", "_default")

    def __init__(
        self, level: float = None, mono_level: float = None, filter_band: float = None, filter_width: float = None
    ):
        super().__init__()
        self.level = level
        self.mono_level = mono_level
        self.filter_band = filter_band
        self.filter_width = filter_width

    def to_dict(self) -> dict[str, float | bool | None]:
        return {
            "level": self.level,
            "mono_level": self.mono_level,
            "filter_band": self.filter_band,
            "filter_width": self.filter_width,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | bool | None]) -> Karaoke:
        return cls(
            level=data["level"],
            mono_level=data["mono_level"],
            filter_band=data["filter_band"],
            filter_width=data["filter_width"],
        )

    def __repr__(self):
        return (
            f"<Karaoke: level={self.level}, mono_level={self.mono_level}, "
            f"filter_band={self.filter_band}, filter_width={self.filter_width}>"
        )

    @property
    def level(self) -> float | None:
        return self._level

    @level.setter
    def level(self, v: float | None):
        self._level = v

    @property
    def mono_level(self) -> float | None:
        return self._mono_level

    @mono_level.setter
    def mono_level(self, v: float | None):
        self._mono_level = v

    @property
    def filter_band(self) -> float | None:
        return self._filter_band

    @filter_band.setter
    def filter_band(self, v: float | None):
        self._filter_band = v

    @property
    def filter_width(self) -> float:
        return self._filter_width

    @filter_width.setter
    def filter_width(self, v: float | None):
        self._filter_width = v

    @classmethod
    def default(cls) -> Karaoke:
        return cls()

    def get(self) -> dict[str, float]:
        if self.off:
            return {}
        response = {}
        if self.level is not None:
            response["level"] = self.level
        if self.mono_level is not None:
            response["monoLevel"] = self.mono_level
        if self.filter_band is not None:
            response["filterBand"] = self.filter_band
        if self.filter_width is not None:
            response["filterWidth"] = self.filter_width
        return response

    def reset(self) -> None:
        self.level = self.mono_level = self.filter_band = self.filter_width = None
