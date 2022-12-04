from __future__ import annotations

import dataclasses
from typing import Literal, Union

from pylav.nodes.api.responses.filters import Filters
from pylav.nodes.api.responses.misc import Git, Plugin, Version
from pylav.nodes.api.responses.playlists import Info
from pylav.nodes.api.responses.track import Track


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LoadException:
    severity: Literal["COMMON", "SUSPICIOUS", "FAULT"]
    message: str | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Exception(LoadException):  # noqa
    cause: str | None = None  # This is only optional so that inheritance in python works


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackLoaded:
    loadType: Literal["TRACK_LOADED"]
    playlistInfo: Info | dict
    tracks: list[Track | dict] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.playlistInfo, dict):
            object.__setattr__(self, "playlistInfo", Info(**self.playlistInfo))
        temp = []
        for t in self.tracks:
            if isinstance(t, Track) or (isinstance(t, dict) and (t := Track(**t))):
                temp.append(t)
        object.__setattr__(self, "tracks", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class PlaylistLoaded:
    loadType: Literal["PLAYLIST_LOADED"]
    playlistInfo: Info | dict
    tracks: list[Track | dict] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.playlistInfo, dict):
            object.__setattr__(self, "playlistInfo", Info(**self.playlistInfo))
        temp = []
        for t in self.tracks:
            if isinstance(t, Track) or (isinstance(t, dict) and (t := Track(**t))):
                temp.append(t)
        object.__setattr__(self, "tracks", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class SearchResult:
    loadType: Literal["SEARCH_RESULT"]
    playlistInfo: Info | dict
    tracks: list[Track | dict] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.playlistInfo, dict):
            object.__setattr__(self, "playlistInfo", Info(**self.playlistInfo))
        temp = []
        for t in self.tracks:
            if isinstance(t, Track) or (isinstance(t, dict) and (t := Track(**t))):
                temp.append(t)
        object.__setattr__(self, "tracks", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class NoMatches:
    loadType: Literal["NO_MATCHES"]
    playlistInfo: Info | dict
    tracks: list[Track | dict] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.playlistInfo, dict):
            object.__setattr__(self, "playlistInfo", Info(**self.playlistInfo))
        temp = []
        for t in self.tracks:
            if isinstance(t, Track) or (isinstance(t, dict) and (t := Track(**t))):
                temp.append(t)
        object.__setattr__(self, "tracks", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LoadFailed:
    loadType: Literal["LOAD_FAILED"]
    exception: LoadException | dict
    playlistInfo: Info | dict
    tracks: list[Track | dict] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.playlistInfo, dict):
            object.__setattr__(self, "playlistInfo", Info(**self.playlistInfo))
        temp = []
        for t in self.tracks:
            if isinstance(t, Track) or (isinstance(t, dict) and (t := Track(**t))):
                temp.append(t)
        object.__setattr__(self, "tracks", temp)


LoadTrackResponses = Union[
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
    plugins: list[Plugin] | dict

    def __post_init__(self):

        if isinstance(self.version, dict):
            object.__setattr__(self, "version", Version(**self.version))
        if isinstance(self.git, dict):
            object.__setattr__(self, "git", Git(**self.git))
        temp = []
        for p in self.plugins.get("plugins", []):
            if isinstance(p, Plugin) or (isinstance(p, dict) and (p := Plugin(**p))):
                temp.append(p)
        object.__setattr__(self, "plugins", temp)


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class VoiceState:
    token: str
    endpoint: str
    sessionId: str
    connected: bool | None = None
    ping: int | None = -1

    def to_dict(self) -> dict[str, str | bool | int | None]:
        return {
            "token": self.token,
            "endpoint": self.endpoint,
            "sessionId": self.sessionId,
            "connected": self.connected,
            "ping": self.ping,
        }

    def __repr__(self) -> str:
        return (
            f"<VoiceStateObject(token={None if not self.token else 'OBFUSCATED'} "
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

    def __post_init__(self):
        if isinstance(self.voice, dict):
            object.__setattr__(self, "voice", VoiceState(**self.voice))
        if isinstance(self.filters, dict):
            object.__setattr__(self, "filters", Filters(**self.filters))
        if isinstance(self.track, dict):
            object.__setattr__(self, "track", Track(**self.track))

    def to_dict(
        self,
    ) -> dict[
        str,
        str  # guildId
        | int  # volume
        | bool  # Paused
        | None  # Track
        | dict[str, str | bool | int | None]  # Voice
        | dict[str, dict[str, float | int] | float | list[dict[str, float | int]] | None]  # Filters
        | dict[str, str | int | bool | None | dict[str, str | int | bool | None]],  # Track
    ]:
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