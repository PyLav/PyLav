from __future__ import annotations

import dataclasses
from typing import Literal  # noqa

from pylav.nodes.api.responses.exceptions import LavalinkException as TrackExceptionClass
from pylav.nodes.api.responses.player import State
from pylav.nodes.api.responses.track import Track


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class CPU:
    cores: int
    systemLoad: float
    lavalinkLoad: float


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Memory:
    free: int
    allocated: int
    reservable: int
    used: int


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Frame:
    sent: int
    nulled: int
    deficit: int


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Message:
    op: str


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Ready(Message):
    sessionId: str
    resumed: bool


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Stats(Message):
    players: int
    playingPlayers: int
    uptime: int
    memory: Memory
    cpu: CPU
    frameStats: Frame | None = None
    uptime_seconds: int = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "uptime_seconds", self.uptime / 1000)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class PlayerUpdate(Message):
    guildId: str
    state: State


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackStart(Message):
    op: Literal["event"]
    type: Literal["TrackStartEvent"]
    guildId: str
    track: Track


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackStuck(Message):
    op: Literal["event"]
    type: Literal["TrackStuckEvent"]
    guildId: str
    track: Track
    thresholdMs: int


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackEnd(Message):
    op: Literal["event"]
    type: Literal["TrackEndEvent"]
    guildId: str
    track: Track
    reason: Literal["finished", "loadFailed", "stopped", "replaced", "cleanup"]


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackException(Message):
    op: Literal["event"]
    type: Literal["TrackExceptionEvent"]
    guildId: str
    track: Track
    exception: TrackExceptionClass


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Closed(Message):
    op: Literal["event"]
    type: Literal["WebSocketClosedEvent"]
    guildId: str
    code: int
    reason: str
    byRemote: bool
