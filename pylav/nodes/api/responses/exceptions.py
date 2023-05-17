from __future__ import annotations

import dataclasses
from typing import Literal


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LoadException:
    severity: Literal["common", "suspicious", "fault"]
    message: str | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkException(LoadException):
    cause: str | None = None  # This is only optional so that inheritance in python works
