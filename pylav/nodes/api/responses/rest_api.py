from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Literal, TypeAlias, Union  # noqa

from pylav.nodes.api.responses.exceptions import LoadException
from pylav.nodes.api.responses.filters import Filters
from pylav.nodes.api.responses.misc import Git, Plugin, Version
from pylav.nodes.api.responses.playlists import Info
from pylav.nodes.api.responses.shared import PlaylistPluginInfo
from pylav.nodes.api.responses.track import Track
from pylav.nodes.api.responses.websocket import CPU, Frame, Memory
from pylav.type_hints.dict_typing import JSON_DICT_TYPE


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class BaseTrackResponse:
    playlistInfo: Info | None
    pluginInfo: PlaylistPluginInfo | None
    exception: LoadException | None
    tracks: list[Track]

    def __post_init__(self):
        if self.pluginInfo is None:
            object.__setattr__(self, "pluginInfo", PlaylistPluginInfo(kwargs=None))


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackLoaded(BaseTrackResponse):  # noqa
    loadType: Literal["TRACK_LOADED"]


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class PlaylistLoaded(BaseTrackResponse):  # noqa
    loadType: Literal["PLAYLIST_LOADED"]


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class SearchResult(BaseTrackResponse):  # noqa
    loadType: Literal["SEARCH_RESULT"]


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class NoMatches(BaseTrackResponse):  # noqa
    loadType: Literal["NO_MATCHES"]


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LoadFailed(BaseTrackResponse):  # noqa
    loadType: Literal["LOAD_FAILED"]


LoadTrackResponses: TypeAlias = Union[
    TrackLoaded,
    PlaylistLoaded,
    NoMatches,
    LoadFailed,
    SearchResult,
]


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
    connected: bool | None = None
    ping: int | None = -1

    def to_dict(self) -> JSON_DICT_TYPE:
        return {
            "token": self.token,
            "endpoint": self.endpoint,
            "sessionId": self.sessionId,
            "connected": self.connected,
            "ping": self.ping,
        }

    def __repr__(self) -> str:
        return (
            f"<VoiceStateObject(token={'OBFUSCATED' if self.token else None} "
            f"endpoint={self.endpoint} "
            f"sessionId={self.sessionId} "
            f"connected={self.connected} "
            f"ping={self.ping})"
        )


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkPlayer:
    guildId: str
    volume: int
    paused: bool
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
