from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Echo(FilterMixin):
    __slots__ = ("_delay", "_decay", "_off", "_default")

    def __init__(self, delay: float = None, decay: float = None):
        super().__init__()
        self.delay = delay
        self.decay = decay
        self.off = all(v is None for v in [delay, decay])

    def to_dict(self) -> dict[str, float | bool | None]:
        return {
            "delay": self.delay,
            "decay": self.decay,
            "off": self.off,
        }

    def to_json(self) -> dict[str, float | None]:
        return {
            "delay": self.delay,
            "decay": self.decay,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | bool | None]) -> Echo:
        c = cls(delay=data["delay"], decay=data["decay"])
        c.off = data["off"]
        return c

    def __repr__(self):
        return f"<Echo: delay={self.delay}, decay={self.decay}>"

    @property
    def delay(self) -> float | None:
        return self._delay

    @delay.setter
    def delay(self, v: float | None):
        if v is None:
            self._delay = None
            self.off = all(
                v is None
                for v in [getattr(self, attr, None) for attr in self.__slots__ if attr not in {"_off", "_default"}]
            )
            return
        if v < 0:
            raise ValueError(f"Delay must be must be greater than 0, not {v}")
        self._delay = v
        self.off = False

    @property
    def decay(self) -> float | None:
        return self._decay

    @decay.setter
    def decay(self, v: float | None):
        if v is None:
            self._decay = v
            self.off = all(
                v is None
                for v in [getattr(self, attr, None) for attr in self.__slots__ if attr not in {"_off", "_default"}]
            )
            return
        if not (0.0 < v <= 1.0):
            raise ValueError(f"Decay must be must be 0.0 < x ≤ 1.0, not {v}")
        self._decay = v
        self.off = False

    @classmethod
    def default(cls) -> Echo:
        return cls()

    def get(self) -> dict[str, float]:
        if self.off:
            return {}
        response = {}
        if self.delay is not None:
            response["delay"] = self.delay
        if self.decay is not None:
            response["decay"] = self.decay
        return response

    def reset(self) -> None:
        self.delay = self.decay = None
        self.off = True
