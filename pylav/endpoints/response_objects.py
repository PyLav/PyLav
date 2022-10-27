import dataclasses
from typing import Annotated, Literal, Union

from pylav.types import ValueRange


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackInfoObject:
    identifier: str
    isSeekable: bool
    author: str
    length: int
    title: str
    isStream: bool
    uri: str | None = None
    position: int | None = 0
    sourceName: str | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class PlaylistInfoObject:
    name: str
    selectedTrack: int = -1


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkTrackObject:
    info: TrackInfoObject
    encoded: str | None = None
    track: str | None = None

    def __post_init__(self):
        if self.encoded is None:
            object.__setattr__(self, "encoded", self.track)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class PlayerStateObject:
    time: int = 0
    connected: bool = False
    ping: int = -1
    position: int | None = 0


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkOpObject:
    op: str


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkReadyOpObject(LavalinkOpObject):
    sessionId: str
    resumed: bool | None = False


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkStatCPUObject:
    cores: int
    systemLoad: float
    lavalinkLoad: float


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkStatsMemoryObject:
    free: int
    allocated: int
    reservable: int
    used: int


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkStatsFrameStatsObject:
    sent: int
    nulled: int
    deficit: int


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkStatsOpObject(LavalinkOpObject):
    players: int
    playingPlayers: int
    uptime: int
    memory: LavalinkStatsMemoryObject
    cpu: LavalinkStatCPUObject
    frameStats: LavalinkStatsFrameStatsObject | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkPlayerUpdateObject(LavalinkOpObject):
    guildId: str
    state: PlayerStateObject


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackStartEventOpObject(LavalinkOpObject):
    op: Literal["event"]
    guildId: str
    type: Literal["TrackStartEvent"]
    encodedTrack: str = None
    track: str | None = None

    def __post_init__(self):
        if self.encodedTrack is None:
            object.__setattr__(self, "encodedTrack", self.track)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackEndEventOpObject(LavalinkOpObject):
    op: Literal["event"]
    guildId: str
    type: Literal["TrackEndEvent"]
    reason: Literal["FINISHED", "LOAD_FAILED", "STOPPED", "REPLACED", "CLEANUP"]
    encodedTrack: str = None
    track: str | None = None

    def __post_init__(self):
        if self.encodedTrack is None:
            object.__setattr__(self, "encodedTrack", self.track)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LoadExceptionObject:
    severity: Literal["COMMON", "SUSPICIOUS", "FAULT"]
    message: str | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackExceptionObject(LoadExceptionObject):
    cause: str = None  # This is only optional so that inheritance in python works


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackExceptionEventOpObject:
    op: Literal["event"]
    guildId: str
    type: Literal["TrackExceptionEvent"]
    exception: TrackExceptionObject
    encodedTrack: str = None
    track: str | None = None

    def __post_init__(self):
        if self.encodedTrack is None:
            object.__setattr__(self, "encodedTrack", self.track)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackStuckEventOpObject:
    op: Literal["event"]
    guildId: str
    type: Literal["TrackStuckEvent"]
    thresholdMs: int
    encodedTrack: str = None
    track: str | None = None

    def __post_init__(self):
        if self.encodedTrack is None:
            object.__setattr__(self, "encodedTrack", self.track)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class WebSocketClosedEventOpObject:
    op: Literal["event"]
    guildId: str
    type: Literal["WebSocketClosedEvent"]
    code: int
    reason: str
    byRemote: bool


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class SegmentObject:
    category: str
    start: str
    end: str


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class SegmentsLoadedEventObject:
    op: Literal["event"]
    guildId: str
    type: Literal["SegmentsLoadedEvent"]
    segments: list[SegmentObject]


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class SegmentSkippedEventOpObject:
    op: Literal["event"]
    guildId: str
    type: Literal["SegmentSkippedEvent"]
    segment: SegmentObject


LavalinkEventOpObjects = Union[
    TrackStartEventOpObject,
    TrackEndEventOpObject,
    TrackExceptionEventOpObject,
    TrackStuckEventOpObject,
    WebSocketClosedEventOpObject,
    SegmentsLoadedEventObject,
    SegmentSkippedEventOpObject,
]


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class VoiceStateObject:
    token: str
    endpoint: str
    sessionId: str
    connected: bool | None = None
    ping: int | None = -1


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class ValueRangeObject:
    min: float
    max: float

    def validate_value(self, x):
        if not (self.min <= x <= self.max):
            raise ValueError(f"{x} must be in range({self.min}, {self.max})")


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class EqualizerBandObject:
    band: Annotated[int | None, ValueRange(min=0, max=14)]
    gain: Annotated[float | None, ValueRange(min=-0.25, max=1.0)]


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class KaraokeObject:
    level: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    monoLevel: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    filterBand: float | None = None
    filterWidth: float | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TimescaleObject:
    speed: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None
    pitch: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None
    rate: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TremoloObject:
    frequency: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None
    depth: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class VibratoObject:
    frequency: Annotated[float | None, ValueRange(min=0, max=14)] = None
    depth: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class RotationObject:
    rotationHz: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class DistortionObject:
    sinOffset: float | None = None
    sinScale: float | None = None
    cosOffset: float | None = None
    cosScale: float | None = None
    tanOffset: float | None = None
    tanScale: float | None = None
    offset: float | None = None
    scale: float | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class ChannelMixObject:
    leftToLeft: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    leftToRight: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    rightToLeft: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    rightToRight: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LowPassObject:
    smoothing: Annotated[float | None, ValueRange(min=1.0, max=float("inf"))] = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class EchoObject:
    delay: Annotated[int | None, ValueRange(min=0, max=float("inf"))] = None
    decay: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class FiltersObject:
    volume: float | None = None
    equalizer: list[EqualizerBandObject] | None = dataclasses.field(default_factory=list)
    karaoke: KaraokeObject | None = dataclasses.field(default_factory=dict)
    timescale: TimescaleObject | None = dataclasses.field(default_factory=dict)
    tremolo: TremoloObject | None = dataclasses.field(default_factory=dict)
    vibrato: VibratoObject | None = dataclasses.field(default_factory=dict)
    rotation: RotationObject | None = dataclasses.field(default_factory=dict)
    distortion: DistortionObject | None = dataclasses.field(default_factory=dict)
    channelMix: ChannelMixObject | None = dataclasses.field(default_factory=dict)
    lowPass: LowPassObject | None = dataclasses.field(default_factory=dict)
    echo: EchoObject | None = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkPlayerObject:
    guildId: str
    volume: int
    paused: bool
    voice: VoiceStateObject
    filters: FiltersObject | None = None
    track: LavalinkTrackObject | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkTrackLoadedObject:
    loadType: Literal["TRACK_LOADED"]
    playlistInfo: PlaylistInfoObject
    tracks: list[LavalinkTrackObject] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkPlaylistLoadedObject:
    loadType: Literal["PLAYLIST_LOADED"]
    playlistInfo: PlaylistInfoObject
    tracks: list[LavalinkTrackObject] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkSearchResultObject:
    loadType: Literal["SEARCH_RESULT"]
    playlistInfo: PlaylistInfoObject
    tracks: list[LavalinkTrackObject] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkNoMatchesObject:
    loadType: Literal["NO_MATCHES"]
    playlistInfo: PlaylistInfoObject
    tracks: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkLoadFailedObject:
    loadType: Literal["LOAD_FAILED"]
    exception: LoadExceptionObject
    playlistInfo: PlaylistInfoObject
    tracks: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class VersionObject:
    semver: str
    major: int
    minor: int
    patch: int
    preRelease: str | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class GitObject:
    branch: str
    commit: str
    commitTime: int


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class PluginObject:
    name: str
    version: str


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkInfoObject:
    version: VersionObject
    buildTime: int
    git: GitObject
    jvm: str
    lavaplayer: str
    sourceManagers: list[str]
    plugins: list[PluginObject]


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class IPBlockObject:
    type: Literal["Inet4Address", "Inet6Address"]
    size: str


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class FailingAddressObject:
    address: str
    failingTimestamp: int
    failingTimes: str


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class RoutePlannerDetailObject:
    ipBlock: IPBlockObject
    failingAddresses: list[FailingAddressObject]
    rotateIndex: str
    ipIndex: str
    currentAddress: str
    currentAddressIndex: str
    blockIndex: str


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class RoutePlannerStatusResponseObject:
    type: Literal["RotatingIpRoutePlanner", "NanoIpRoutePlanner", "RotatingNanoIpRoutePlanner"] | None = None
    details: RoutePlannerDetailObject | None = None


LavalinkLoadTrackObjects = Union[
    LavalinkTrackLoadedObject
    | LavalinkPlaylistLoadedObject
    | LavalinkNoMatchesObject
    | LavalinkLoadFailedObject
    | LavalinkSearchResultObject
]
