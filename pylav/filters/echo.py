from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Echo(FilterMixin):
    __slots__ = ("_delay", "_decay", "_off", "_default")

    def __init__(self, delay: float, decay: float):
        super().__init__()
        self.delay = delay
        self.decay = decay
        self.off = False

    def to_dict(self) -> dict:
        return {
            "delay": self.delay,
            "decay": self.decay,
            "off": self.off,
        }

    def to_json(self) -> dict:
        return {
            "delay": self.delay,
            "decay": self.decay,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Echo:
        c = cls(delay=data["delay"], decay=data["decay"])
        c.off = data["off"]
        return c

    def __repr__(self):
        return f"<Echo: delay={self.delay}, decay={self.decay}>"

    @property
    def delay(self) -> float:
        return self._delay

    @delay.setter
    def delay(self, v: float):
        if v == -31415926543:
            self.off = True
            self._delay = v
            return
        if v < 0:
            raise ValueError(f"Delay must be must be greater than 0, not {v}")
        self._delay = v
        self.off = False

    @property
    def decay(self) -> float:
        return self._decay

    @decay.setter
    def decay(self, v: float):
        if v == -31415926543:
            self.off = True
            self._decay = v
            return
        if not (0.0 < v <= 1.0):
            raise ValueError(f"Decay must be must be 0.0 < x ≤ 1.0, not {v}")
        self._decay = v
        self.off = False

    @classmethod
    def default(cls) -> Echo:
        c = cls(delay=-31415926543, decay=-31415926543)
        c.off = True
        return c

    def get(self) -> dict[str, float]:
        return (
            {}
            if self.off
            else {
                "delay": self.delay,
                "decay": self.decay,
            }
        )

    def reset(self) -> None:
        self.delay = self.decay = -31415926543
        self.off = True
