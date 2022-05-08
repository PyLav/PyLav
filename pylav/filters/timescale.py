from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Timescale(FilterMixin):
    def __init__(self, speed: float, pitch: float, rate: float):
        self.speed = speed
        self.pitch = pitch
        self.rate = rate
        self.off = False

    def to_dict(self) -> dict:
        return {
            "speed": self.speed,
            "pitch": self.pitch,
            "rate": self.rate,
            "off": self.off,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Timescale:
        c = cls(speed=data["speed"], pitch=data["pitch"], rate=data["rate"])
        c.off = data["off"]
        return c

    def __repr__(self):
        return f"<Timescale: speed={self.speed}, pitch={self.pitch}, rate={self.rate}>"

    @property
    def speed(self) -> float:
        return self._speed

    @speed.setter
    def speed(self, v: float):
        self._speed = v
        self.off = False

    @property
    def pitch(self) -> float:
        return self._pitch

    @pitch.setter
    def pitch(self, v: float):
        self._pitch = v
        self.off = False

    @property
    def rate(self) -> float:
        return self._rate

    @rate.setter
    def rate(self, v: float):
        self._rate = v
        self.off = False

    @classmethod
    def default(cls) -> Timescale:
        c = cls(speed=1.0, pitch=1.0, rate=1.0)
        c.off = True
        return c

    def get(self) -> dict[str, float]:
        if self.off:
            return {}
        return {
            "speed": self.speed,
            "pitch": self.pitch,
            "rate": self.rate,
        }

    def reset(self) -> None:
        self.speed = 1.0
        self.pitch = 1.0
        self.rate = 1.0
        self.off = True
