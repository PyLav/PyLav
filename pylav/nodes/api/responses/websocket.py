from __future__ import annotations

import dataclasses
from typing import Literal  # noqa

from pylav.nodes.api.responses.player import State
from pylav.nodes.api.responses.rest_api import LavalinkException as TrackExceptionClass


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
    op: str | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Ready(Message):
    sessionId: str | None = None
    resumed: bool = False


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Stats(Message):
    players: int = 0
    playingPlayers: int = 0
    uptime: int = 0
    memory: Memory | None | dict = None
    cpu: CPU | None | dict = None
    frameStats: Frame | None | dict = None
    uptime_seconds: int = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "uptime_seconds", self.uptime / 1000)
        if isinstance(self.memory, dict):
            object.__setattr__(self, "memory", Memory(**self.memory))
        if isinstance(self.cpu, dict):
            object.__setattr__(self, "cpu", CPU(**self.cpu))
        if isinstance(self.frameStats, dict):
            object.__setattr__(self, "frameStats", Frame(**self.frameStats))


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class PlayerUpdate(Message):
    guildId: str | None = None
    state: State | dict | None = None

    def __post_init__(self) -> None:
        if isinstance(self.state, dict):
            object.__setattr__(self, "state", State(**self.state))


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackStart(Message):
    op: Literal["event"] = "event"
    guildId: str | None = None
    type: Literal["TrackStartEvent"] = "TrackStartEvent"
    encodedTrack: str | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackStuck(Message):
    op: Literal["event"] = "event"
    guildId: str | None = None
    type: Literal["TrackStuckEvent"] = "TrackStuckEvent"
    thresholdMs: int | None = None
    encodedTrack: str | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackEnd(Message):
    op: Literal["event"] = "event"
    guildId: str | None = None
    type: Literal["TrackEndEvent"] = "TrackEndEvent"
    reason: Literal["FINISHED", "LOAD_FAILED", "STOPPED", "REPLACED", "CLEANUP"] | None = None
    encodedTrack: str | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackException(Message):
    op: Literal["event"] = "event"
    guildId: str | None = None
    type: Literal["TrackExceptionEvent"] = "TrackExceptionEvent"
    exception: TrackExceptionClass | dict | None = None
    encodedTrack: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.exception, dict):
            object.__setattr__(self, "exception", TrackExceptionClass(**self.exception))


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Closed(Message):
    op: Literal["event"] = "event"
    guildId: str | None = None
    type: Literal["WebSocketClosedEvent"] = "WebSocketClosedEvent"
    code: int | None = None
    reason: str | None = None
    byRemote: bool = False
