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
    failingAddresses: list[FailingAddress]
    rotateIndex: str
    ipIndex: str
    currentAddress: str
    currentAddressIndex: str
    blockIndex: str

    def __post_init__(self):
        temp = []
        for s in self.failingAddresses:
            if isinstance(s, FailingAddress) or (isinstance(s, dict) and (s := FailingAddress(**s))):
                temp.append(s)
        object.__setattr__(self, "failingAddresses", temp)
        if isinstance(self.ipBlock, dict):
            object.__setattr__(self, "ipBlock", IPBlock(**self.ipBlock))


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Status:
    type: Literal["RotatingIpRoutePlanner", "NanoIpRoutePlanner", "RotatingNanoIpRoutePlanner"] | None = None
    details: Details | None | dict = None

    def __post_init__(self):
        if isinstance(self.details, dict):
            object.__setattr__(self, "details", Details(**self.details))
