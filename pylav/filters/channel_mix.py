from __future__ import annotations

from pylav.filters.utils import FilterMixin


class ChannelMix(FilterMixin):
    __slots__ = ("_left_to_left", "_left_to_right", "_right_to_left", "_right_to_right", "_off", "_default")

    def __init__(
        self,
        left_to_left: float = None,
        left_to_right: float = None,
        right_to_left: float = None,
        right_to_right: float = None,
    ):
        super().__init__()
        self.left_to_left = left_to_left
        self.left_to_right = left_to_right
        self.right_to_left = right_to_left
        self.right_to_right = right_to_right
        self.off = all(v is None for v in [left_to_left, left_to_right, right_to_left, right_to_right])

    def to_dict(self) -> dict[str, float | None | bool]:
        return {
            "leftToLeft": self.left_to_left,
            "leftToRight": self.left_to_right,
            "rightToLeft": self.right_to_left,
            "rightToRight": self.right_to_right,
            "off": self.off,
        }

    def to_json(self) -> dict[str, float | None]:
        return {
            "leftToLeft": self.left_to_left,
            "leftToRight": self.left_to_right,
            "rightToLeft": self.right_to_left,
            "rightToRight": self.right_to_right,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | bool | None]) -> ChannelMix:
        c = cls(
            left_to_left=data["leftToLeft"],
            left_to_right=data["leftToRight"],
            right_to_left=data["rightToLeft"],
            right_to_right=data["rightToRight"],
        )
        c.off = data["off"]
        return c

    def __repr__(self):
        return (
            f"<ChannelMix: left_to_left={self.left_to_left}, "
            f"left_to_right={self.left_to_right}, "
            f"right_to_left={self.right_to_left}, "
            f"right_to_right={self.right_to_right}>"
        )

    @property
    def left_to_left(self) -> float | None:
        return self._left_to_left

    @left_to_left.setter
    def left_to_left(self, v: float | None):
        self._left_to_left = v
        self.off = all(
            v is None
            for v in [getattr(self, attr, None) for attr in self.__slots__ if attr not in {"_off", "_default"}]
        )

    @property
    def left_to_right(self) -> float | None:
        return self._left_to_right

    @left_to_right.setter
    def left_to_right(self, v: float | None):
        self._left_to_right = v
        self.off = all(
            v is None
            for v in [getattr(self, attr, None) for attr in self.__slots__ if attr not in {"_off", "_default"}]
        )

    @property
    def right_to_left(self) -> float | None:
        return self._right_to_left

    @right_to_left.setter
    def right_to_left(self, v: float | None):
        self._right_to_left = v
        self.off = all(
            v is None
            for v in [getattr(self, attr, None) for attr in self.__slots__ if attr not in {"_off", "_default"}]
        )

    @property
    def right_to_right(self) -> float | None:
        return self._right_to_right

    @right_to_right.setter
    def right_to_right(self, v: float | None):
        self._right_to_right = v
        self.off = all(
            v is None
            for v in [getattr(self, attr, None) for attr in self.__slots__ if attr not in {"_off", "_default"}]
        )

    @classmethod
    def default(cls) -> ChannelMix:
        return cls()

    def get(self) -> dict[str, float]:
        if self.off:
            return {}
        response = {}
        if self.left_to_left is not None:
            response["leftToLeft"] = self.left_to_left
        if self.left_to_right is not None:
            response["leftToRight"] = self.left_to_right
        if self.right_to_left is not None:
            response["rightToLeft"] = self.right_to_left
        if self.right_to_right is not None:
            response["rightToRight"] = self.right_to_right
        return response

    def reset(self) -> None:
        self.right_to_right = self.right_to_left = self.left_to_right = self.left_to_left = None
        self.off = True
