from __future__ import annotations

from pylav.players.filters.misc import FilterMixin


class Timescale(FilterMixin):
    __slots__ = ("_speed", "_pitch", "_rate", "_default")

    def __init__(self, speed: float | None = None, pitch: float | None = None, rate: float | None = None) -> None:
        super().__init__()
        self.speed = speed
        self.pitch = pitch
        self.rate = rate

    def to_dict(self) -> dict[str, float | bool | None]:
        return {
            "speed": self.speed,
            "pitch": self.pitch,
            "rate": self.rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | bool | None]) -> Timescale:
        return cls(speed=data["speed"], pitch=data["pitch"], rate=data["rate"])

    def __repr__(self) -> str:
        return f"<Timescale: speed={self.speed}, pitch={self.pitch}, rate={self.rate}>"

    @property
    def speed(self) -> float | None:
        return self._speed

    @speed.setter
    def speed(self, v: float | None) -> None:
        self._speed = v

    @property
    def pitch(self) -> float | None:
        return self._pitch

    @pitch.setter
    def pitch(self, v: float | None) -> None:
        self._pitch = v

    @property
    def rate(self) -> float | None:
        return self._rate

    @rate.setter
    def rate(self, v: float | None) -> None:
        self._rate = v

    @classmethod
    def default(cls) -> Timescale:
        return cls()

    def get(self) -> dict[str, float]:
        if self.off:
            return {}
        response = {}
        if self.speed is not None:
            response["speed"] = self.speed
        if self.pitch is not None:
            response["pitch"] = self.pitch
        if self.rate is not None:
            response["rate"] = self.rate
        return response

    def reset(self) -> None:
        self.speed = self.pitch = self.rate = None

    def adjust_position(self, position: float | int) -> float:
        if self.speed is None and self.rate is None:
            return position
        if self.rate is None:
            return position * self.speed
        return position + (position * (self.speed - 1))
