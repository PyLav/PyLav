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

    @staticmethod
    def _decrease(value: float | int, percentage: float | int) -> float:
        return value / (1 + percentage)

    @staticmethod
    def _increase(value: float | int, percentage: float | int) -> float:
        return value * (1 + percentage)

    def _get_percentages(self) -> tuple[float, float]:
        if self.speed is None:
            speed = 0
        elif self.speed >= 1:
            speed = self.speed - 1
        else:
            speed = 1 - self.speed
        if self.rate is None:
            rate = 0
        elif self.rate >= 1:
            rate = self.rate - 1
        else:
            rate = 1 - self.rate
        return speed, rate

    def adjust_position(self, position: float | int) -> int:
        if self.speed is None and self.rate is None:
            return int(position)
        speed, rate = self._get_percentages()
        if self.rate is None:
            return int(self._decrease(position, speed) if self.speed >= 1 else self._increase(position, speed))
        if self.speed is None:
            return int(
                self._decrease(position, self.rate - 1) if self.rate >= 1 else self._increase(position, 1 - self.rate)
            )
        if self.speed >= 1 and self.rate >= 1:
            return int(self._decrease(position, (self.speed - 1) + (self.rate - 1)))
        elif self.speed >= 1 > self.rate:
            return int(self._decrease(self._increase(position, 1 - self.rate), self.speed - 1))

        elif self.speed < 1 <= self.rate:
            return int(self._decrease(self._increase(position, self.speed - 1), 1 - self.rate))
        else:
            return int(self._increase(position, (1 - self.speed) + (1 - self.rate)))

    def reverse_position(self, position: float | int) -> int:
        if self.speed is None and self.rate is None:
            return int(position)
        speed, rate = self._get_percentages()
        if self.rate is None:
            return int(self._increase(position, speed) if self.speed >= 1 else self._decrease(position, speed))
        if self.speed is None:
            return int(
                self._increase(position, self.rate - 1) if self.rate >= 1 else self._decrease(position, 1 - self.rate)
            )
        if self.speed >= 1 and self.rate >= 1:
            return int(self._increase(position, (self.speed - 1) + (self.rate - 1)))
        elif self.speed >= 1 > self.rate:
            return int(self._increase(self._decrease(position, 1 - self.rate), self.speed - 1))

        elif self.speed < 1 <= self.rate:
            return int(self._increase(self._decrease(position, self.speed - 1), 1 - self.rate))
        else:
            return int(self._decrease(position, (1 - self.speed) + (1 - self.rate)))
