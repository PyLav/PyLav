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
    ipBlock: IPBlock | dict
    failingAddresses: list[FailingAddress | dict]
    rotateIndex: str
    ipIndex: str
    currentAddress: str
    currentAddressIndex: str
    blockIndex: str

    def __post_init__(self) -> None:
        if isinstance(self.ipBlock, dict):
            object.__setattr__(self, "ipBlock", IPBlock(**self.ipBlock))
        temp = []
        for f in self.failingAddresses:
            if isinstance(f, FailingAddress) or (isinstance(f, dict) and (f := FailingAddress(**f))):
                temp.append(f)
        object.__setattr__(self, "failingAddresses", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Status:
    type: Literal["RotatingIpRoutePlanner", "NanoIpRoutePlanner", "RotatingNanoIpRoutePlanner"] | None = None
    details: Details | dict | None = None

    def __post_init__(self) -> None:
        if isinstance(self.details, dict):
            object.__setattr__(self, "details", Details(**self.details))
