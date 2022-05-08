from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Karaoke(FilterMixin):
    def __init__(self, level: float, mono_level: float, filter_band: float, filter_width: float):
        self.level = level
        self.mono_level = mono_level
        self.filter_band = filter_band
        self.filter_width = filter_width
        self.off = False

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "mono_level": self.mono_level,
            "filter_band": self.filter_band,
            "filter_width": self.filter_width,
            "off": self.off,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Karaoke:
        c = cls(
            level=data["level"],
            mono_level=data["mono_level"],
            filter_band=data["filter_band"],
            filter_width=data["filter_width"],
        )
        c.off = data["off"]
        return c

    def __repr__(self):
        return (
            f"<Karaoke: level={self.level}, mono_level={self.mono_level}, "
            f"filter_band={self.filter_band}, filter_width={self.filter_width}>"
        )

    @property
    def level(self) -> float:
        return self._level

    @level.setter
    def level(self, v: float):
        self._level = v
        self.off = False

    @property
    def mono_level(self) -> float:
        return self._mono_level

    @mono_level.setter
    def mono_level(self, v: float):
        self._mono_level = v
        self.off = False

    @property
    def filter_band(self) -> float:
        return self._filter_band

    @filter_band.setter
    def filter_band(self, v: float):
        self._filter_band = v
        self.off = False

    @property
    def filter_width(self) -> float:
        return self._filter_width

    @filter_width.setter
    def filter_width(self, v: float):
        self._filter_width = v
        self.off = False

    @classmethod
    def default(cls) -> Karaoke:
        c = cls(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
        c.off = True
        return c

    def get(self) -> dict[str, float]:
        if self.off:
            return {}
        return {
            "level": self.level,
            "monoLevel": self.mono_level,
            "filterBand": self.filter_band,
            "filterWidth": self.filter_width,
        }

    def reset(self) -> None:
        self.level = 1.0
        self.mono_level = 1.0
        self.filter_band = 220.0
        self.filter_width = 100.0
        self.off = True
