from __future__ import annotations

from typing import Any

__all__ = ("MISSING",)


class MissingSentinel(str):
    def __str__(self) -> str:
        return "MISSING"

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING: Any = MissingSentinel("MISSING")
