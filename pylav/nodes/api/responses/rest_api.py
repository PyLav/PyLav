from __future__ import annotations

import dataclasses
from typing import Literal, TypeAlias, Union

from pylav.exceptions.request import HTTPException
from pylav.nodes.api.responses.exceptions import LoadException
from pylav.nodes.api.responses.filters import Filters
from pylav.nodes.api.responses.misc import Git, Plugin, Version
from pylav.nodes.api.responses.player import State
from pylav.nodes.api.responses.playlists import Info
from pylav.nodes.api.responses.shared import PlaylistPluginInfo, PluginInfo
from pylav.nodes.api.responses.track import Track
from pylav.nodes.api.responses.websocket import CPU, Frame, Memory
from pylav.type_hints.dict_typing import JSON_DICT_TYPE


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class PlaylistData:
    info: Info
    pluginInfo: PlaylistPluginInfo
    tracks: list[Track]

    def __post_init__(self):
        temp = []
        for s in self.tracks:
            if isinstance(s, Track) or (isinstance(s, dict) and (s := Track(**s))):
                temp.append(s)
        object.__setattr__(self, "tracks", temp)

    def to_dict(self) -> JSON_DICT_TYPE:
        return dataclasses.asdict(self)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class BaseTrackResponse:
    loadType: Literal["track", "playlist", "search", "empty", "error"]
    data: Track | PlaylistData | list[Track] | LoadException | None

    def __bool__(self):
        return True

    def to_dict(self) -> JSON_DICT_TYPE:
        return dataclasses.asdict(self)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackResponse(BaseTrackResponse):
    loadType: Literal["track"]
    data: Track


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class PlaylistResponse(BaseTrackResponse):
    loadType: Literal["playlist"]
    data: PlaylistData


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class SearchResponse(BaseTrackResponse):
    loadType: Literal["search"]
    data: list[Track]

    def __post_init__(self):
        temp = []
        for s in self.data:
            if isinstance(s, Track) or (isinstance(s, dict) and (s := Track(**s))):
                temp.append(s)
        object.__setattr__(self, "data", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class EmptyResponse(BaseTrackResponse):
    loadType: Literal["empty"]
    data: None = None

    def __bool__(self):
        return False


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class ErrorResponse(BaseTrackResponse):  # noqa
    loadType: Literal["error"]
    data: LoadException

    def __bool__(self):
        return False


LoadTrackResponses: TypeAlias = Union[
    TrackResponse, PlaylistResponse, EmptyResponse, ErrorResponse, SearchResponse, HTTPException
]


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TextInfo:
    text: str
    plugin: PluginInfo


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LoadSearchResponses:
    tracks: list[Track]
    albums: list[PlaylistData]
    artists: list[PlaylistData]
    playlists: list[PlaylistData]
    plugins: PluginInfo
    texts: list[TextInfo]

    def __post_init__(self):
        temp = []
        for s in self.tracks:
            if isinstance(s, Track) or (isinstance(s, dict) and (s := Track(**s))):
                temp.append(s)
        object.__setattr__(self, "tracks", temp)

    def to_dict(self) -> JSON_DICT_TYPE:
        return dataclasses.asdict(self)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkInfo:
    version: Version
    buildTime: int
    git: Git
    jvm: str
    lavaplayer: str
    sourceManagers: list[str]
    filters: list[str]
    plugins: list[Plugin]

    def __post_init__(self):
        temp = []
        for s in self.plugins:
            if isinstance(s, Plugin) or (isinstance(s, dict) and (s := Plugin(**s))):
                temp.append(s)
        object.__setattr__(self, "plugins", temp)


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class VoiceState:
    token: str
    endpoint: str
    sessionId: str

    def to_dict(self) -> JSON_DICT_TYPE:
        return {
            "token": self.token,
            "endpoint": self.endpoint,
            "sessionId": self.sessionId,
        }

    def __repr__(self) -> str:
        return (
            f"<VoiceStateObject(token={'OBFUSCATED' if self.token else None} "
            f"endpoint={self.endpoint} "
            f"sessionId={self.sessionId})"
        )


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkPlayer:
    guildId: str
    volume: int
    paused: bool
    state: State | dict
    voice: VoiceState | dict
    filters: Filters | dict
    track: Track | dict | None = None

    def __post_init__(self) -> None:
        if isinstance(self.voice, dict):
            object.__setattr__(self, "voice", VoiceState(**self.voice))
        if isinstance(self.filters, dict):
            object.__setattr__(self, "filters", Filters(**self.filters))
        if isinstance(self.track, dict):
            object.__setattr__(self, "track", Track(**self.track))
        if isinstance(self.state, dict):
            object.__setattr__(self, "state", State(**self.state))

    def to_dict(
        self,
    ) -> JSON_DICT_TYPE:
        assert (
            isinstance(self.voice, VoiceState)
            and isinstance(self.filters, Filters)
            and isinstance(self.track, (Track, type(None)))
        )
        return {
            "guildId": self.guildId,
            "volume": self.volume,
            "paused": self.paused,
            "state": self.state.to_dict(),
            "voice": self.voice.to_dict(),
            "filters": self.filters.to_dict(),
            "track": self.track.to_dict() if self.track else None,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Stats:
    players: int
    playingPlayers: int
    uptime: int
    memory: Memory
    cpu: CPU
    frameStats: Frame | None = None
    uptime_seconds: int = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "uptime_seconds", self.uptime / 1000)
