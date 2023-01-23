from __future__ import annotations

import dataclasses
from typing import Literal


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class IPBlock:
    type: Literal["Inet4Address", "Inet6Address"]
    size: str


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class FailingAddress:
    address: str
    failingTimestamp: int
    failingTimes: str


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Details:
    ipBlock: IPBlock
    failingAddresses: list[FailingAddress]
    rotateIndex: str
    ipIndex: str
    currentAddress: str
    currentAddressIndex: str
    blockIndex: str


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Status:
    details: Details | None
    type: Literal["RotatingIpRoutePlanner", "NanoIpRoutePlanner", "RotatingNanoIpRoutePlanner"] | None = None

    def __post_init__(self):
        if isinstance(self.details, dict):
            object.__setattr__(self, "details", Details(**self.details))
