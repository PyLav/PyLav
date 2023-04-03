from __future__ import annotations

import dataclasses
import time
from collections.abc import Iterator
from typing import Any

from discord.backoff import ExponentialBackoff

from pylav.type_hints.generics import ANY_GENERIC_TYPE


class MissingSentinel(str):
    """A sentinel class for missing values."""

    def __str__(self) -> str:
        return "MISSING"

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False

    def __int__(self) -> int:
        return 0

    def __float__(self) -> float:
        return 0.0

    def __len__(self) -> int:
        return 0

    def __iter__(self) -> Iterator:
        return iter([])

    def __getitem__(self, item) -> None:
        return None

    def __getattr__(self, item) -> None:
        return None

    def __divmod__(self, other) -> tuple[int, int]:
        return 0, 0

    def __rdivmod__(self, other) -> tuple[int, int]:
        return 0, 0

    def __floor__(self) -> int:
        return 0

    def __ceil__(self) -> int:
        return 0

    def __round__(self) -> int:
        return 0

    def __trunc__(self) -> int:
        return 0

    def __add__(self, other: ANY_GENERIC_TYPE) -> ANY_GENERIC_TYPE:
        return other

    def __radd__(self, other: ANY_GENERIC_TYPE) -> ANY_GENERIC_TYPE:
        return other

    def __sub__(self, other: ANY_GENERIC_TYPE) -> ANY_GENERIC_TYPE:
        return other

    def __rsub__(self, other: ANY_GENERIC_TYPE) -> ANY_GENERIC_TYPE:
        return other

    def __mul__(self, other: Any) -> int:
        return 0

    def __rmul__(self, other: Any) -> int:
        return 0

    def __matmul__(self, other: Any) -> int:
        return 0

    def __rmatmul__(self, other: Any) -> int:
        return 0

    def __mod__(self, other: Any) -> int:
        return 0

    def __rmod__(self, other: Any) -> int:
        return 0

    def __rdiv__(self, other: Any) -> int:
        return 0

    def __truediv__(self, other: Any) -> int:
        return 0

    def __rtruediv__(self, other: Any) -> int:
        return 0

    def __floordiv__(self, other: Any) -> int:
        return 0

    def __rfloordiv__(self, other: Any) -> int:
        return 0

    def __pow__(self, other: Any) -> int:
        return 0

    def __rpow__(self, other: Any) -> int:
        return 0

    def __lshift__(self, other: Any) -> int:
        return 0

    def __rlshift__(self, other: Any) -> int:
        return 0

    def __le__(self, other: Any) -> bool:
        return True

    def __lt__(self, other: Any) -> bool:
        return True

    def __ge__(self, other: Any) -> bool:
        return False

    def __gt__(self, other: Any) -> bool:
        return False

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, MissingSentinel)

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return 0

    def __contains__(self, item: Any) -> bool:
        return False


MISSING: Any = MissingSentinel("MISSING")


@dataclasses.dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class TimedFeature:
    """A timed feature data wrapper."""

    enabled: bool = False
    time: int = 60

    def to_dict(self) -> dict[str, bool | int]:
        """Convert to dict"""
        return {"enabled": self.enabled, "time": self.time}

    @classmethod
    def from_dict(cls, data: dict[str, bool | int]) -> TimedFeature:
        """Convert from dict"""
        return cls(enabled=data["enabled"], time=data["time"])


class ExponentialBackoffWithReset(ExponentialBackoff):
    """
    Exponential backoff with reset
    """

    def __init__(self, base: int = 1, *, integral: ANY_GENERIC_TYPE = False) -> None:
        super().__init__(base=base, integral=integral)

    def reset(self) -> None:
        """
        Reset the backoff to its initial state.
        """
        self._last_invocation: float = time.monotonic()
        self._exp = 0
