from __future__ import annotations

import dataclasses
from typing import Literal

from pylav.nodes.api.responses.websocket import Message

__all__ = ("Segment", "SegmentsLoaded", "SegmentSkipped")


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Segment:
    category: str
    start: str
    end: str


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class SegmentsLoaded(Message):
    op: Literal["event"] = "event"
    guildId: str | None = None
    type: Literal["SegmentsLoaded"] = "SegmentsLoaded"
    segments: list[Segment | dict] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        temp = []
        for s in self.segments:
            if isinstance(s, Segment) or (isinstance(s, dict) and (s := Segment(**s))):
                temp.append(s)
        object.__setattr__(self, "segments", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class SegmentSkipped(Message):
    op: Literal["event"] = "event"
    guildId: str | None = None
    type: Literal["SegmentSkipped"] = "SegmentSkipped"
    segment: Segment | dict = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.segment, dict):
            object.__setattr__(self, "segment", Segment(**self.segment))
