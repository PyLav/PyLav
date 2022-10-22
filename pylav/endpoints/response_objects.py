import dataclasses
from typing import Annotated, Literal, Union

from pylav.types import ValueRange


@dataclasses.dataclass
class TrackInfoObject:
    identifier: str
    isSeekable: bool
    author: str
    length: int
    title: str
    isStream: bool
    uri: str | None = None
    position: int | None = None
    sourceName: str | None = None


@dataclasses.dataclass
class PlaylistInfoObject:  # noqa
    name: str
    selectedTrack: int


@dataclasses.dataclass
class LavalinkTrackObject:
    info: TrackInfoObject
    encoded: str
    track: str = None


@dataclasses.dataclass
class PlayerStateObject:
    time: int
    connected: bool
    ping: int
    position: int = None


@dataclasses.dataclass
class LavalinkOpObject:
    op: str


@dataclasses.dataclass
class LavalinkReadyOpObject(LavalinkOpObject):
    sessionId: str
    resumed: bool = None


@dataclasses.dataclass
class LavalinkStatCPUObject:
    cores: int
    systemLoad: float
    lavalinkLoad: float


@dataclasses.dataclass
class LavalinkStatsMemoryObject:
    free: int
    allocated: int
    reservable: int
    used: int


@dataclasses.dataclass
class LavalinkStatsFrameStatsObject:
    sent: int
    nulled: int
    deficit: int


@dataclasses.dataclass
class LavalinkStatsOpObject(LavalinkOpObject):
    players: int
    playingPlayers: int
    uptime: int
    memory: LavalinkStatsMemoryObject
    cpu: LavalinkStatCPUObject
    frameStats: LavalinkStatsFrameStatsObject


@dataclasses.dataclass
class LavalinkPlayerUpdateT(LavalinkOpObject):
    guildId: str
    state: PlayerStateObject


@dataclasses.dataclass
class TrackStartEventOpObject(LavalinkOpObject):
    op: Literal["event"]
    guildId: str
    type: Literal["TrackStartEvent"]
    encodedTrack: str
    track: str = None


@dataclasses.dataclass
class TrackEndEventOpObject(LavalinkOpObject):
    op: Literal["event"]
    guildId: str
    type: Literal["TrackEndEvent"]
    reason: Literal["FINISHED", "LOAD_FAILED", "STOPPED", "REPLACED", "CLEANUP"]
    encodedTrack: str
    track: str = None


@dataclasses.dataclass
class LoadExceptionObject:
    message: str
    severity: Literal["COMMON", "SUSPICIOUS", "FAULT"]


@dataclasses.dataclass
class TrackExceptionObject(LoadExceptionObject):
    cause: str


@dataclasses.dataclass
class TrackExceptionEventOpObject:
    op: Literal["event"]
    guildId: str
    type: Literal["TrackExceptionEvent"]
    exception: TrackExceptionObject
    encodedTrack: str
    track: str = None


@dataclasses.dataclass
class TrackStuckEventOpObject:
    op: Literal["event"]
    guildId: str
    type: Literal["TrackStuckEvent"]
    thresholdMs: int
    encodedTrack: str
    track: str = None


@dataclasses.dataclass
class WebSocketClosedEventOpObject:
    op: Literal["event"]
    guildId: str
    type: Literal["WebSocketClosedEvent"]
    code: int
    reason: str
    byRemote: bool


@dataclasses.dataclass
class SegmentObject:
    category: str
    start: str
    end: str


@dataclasses.dataclass
class SegmentsLoadedEventObject:
    op: Literal["event"]
    guildId: str
    type: Literal["SegmentsLoadedEvent"]
    segments: list[SegmentObject]


@dataclasses.dataclass
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


@dataclasses.dataclass
class VoiceStateObject:
    token: str
    endpoint: str
    sessionId: str
    connected: bool = None
    ping: int = None


@dataclasses.dataclass
class ValueRangeObject:
    min: float
    max: float

    def validate_value(self, x):
        if not (self.min <= x <= self.max):
            raise ValueError(f"{x} must be in range({self.min}, {self.max})")


@dataclasses.dataclass
class EqualizerBandObject:
    band: Annotated[int, ValueRange(min=0, max=14)]
    gain: Annotated[float, ValueRange(min=-0.25, max=1.0)]


@dataclasses.dataclass
class KaraokeObject:
    level: Annotated[float, ValueRange(min=0.0, max=1.0)] = None
    monoLevel: Annotated[float, ValueRange(min=0.0, max=1.0)] = None
    filterBand: float = None
    filterWidth: float = None


@dataclasses.dataclass
class TimescaleObject:
    speed: Annotated[float, ValueRange(min=0.0, max=float("inf"))] = None
    pitch: Annotated[float, ValueRange(min=0.0, max=float("inf"))] = None
    rate: Annotated[float, ValueRange(min=0.0, max=float("inf"))] = None


@dataclasses.dataclass
class TremoloObject:
    frequency: Annotated[float, ValueRange(min=0.0, max=float("inf"))] = None
    depth: Annotated[float, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass
class VibratoObject:
    frequency: Annotated[float, ValueRange(min=0, max=14)] = None
    depth: Annotated[float, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass
class RotationObject:
    rotationHz: Annotated[float, ValueRange(min=0.0, max=float("inf"))] = None


@dataclasses.dataclass
class DistortionObject:
    sinOffset: float = None
    sinScale: float = None
    cosOffset: float = None
    cosScale: float = None
    tanOffset: float = None
    tanScale: float = None
    offset: float = None
    scale: float = None


@dataclasses.dataclass
class ChannelMixObject:
    leftToLeft: Annotated[float, ValueRange(min=0.0, max=1.0)] = None
    leftToRight: Annotated[float, ValueRange(min=0.0, max=1.0)] = None
    rightToLeft: Annotated[float, ValueRange(min=0.0, max=1.0)] = None
    rightToRight: Annotated[float, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass
class LowPassObject:
    smoothing: Annotated[float, ValueRange(min=1.0, max=float("inf"))] = None


@dataclasses.dataclass
class EchoObject:
    delay: Annotated[int, ValueRange(min=0, max=float("inf"))] = None
    decay: Annotated[float, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass
class FiltersObject:
    volume: float = None
    equalizer: list[EqualizerBandObject] = dataclasses.field(default_factory=list)
    karaoke: KaraokeObject = dataclasses.field(default_factory=dict)
    timescale: TimescaleObject = dataclasses.field(default_factory=dict)
    tremolo: TremoloObject = dataclasses.field(default_factory=dict)
    vibrato: VibratoObject = dataclasses.field(default_factory=dict)
    rotation: RotationObject = dataclasses.field(default_factory=dict)
    distortion: DistortionObject = dataclasses.field(default_factory=dict)
    channelMix: ChannelMixObject = dataclasses.field(default_factory=dict)
    lowPass: LowPassObject = dataclasses.field(default_factory=dict)
    echo: EchoObject = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class LavalinkPlayerObject:
    guildId: str
    volume: int
    paused: bool
    voice: VoiceStateObject
    filters: FiltersObject
    track: LavalinkTrackObject = None


@dataclasses.dataclass
class LavalinkTrackLoadedObject:
    loadType: Literal["TRACK_LOADED"]
    tracks: list[LavalinkTrackObject]


@dataclasses.dataclass
class LavalinkPlaylistLoadedObject:
    loadType: Literal["PLAYLIST_LOADED"]
    playlistInfo: PlaylistInfoObject
    tracks: list[LavalinkTrackObject]


@dataclasses.dataclass
class LavalinkSearchResultObject:
    loadType: Literal["SEARCH_RESULT"]
    tracks: list[LavalinkTrackObject]


@dataclasses.dataclass
class LavalinkNoMatchesObject:
    loadType: Literal["NO_MATCHES"]
    tracks: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class LavalinkLoadFailedObject:
    loadType: Literal["LOAD_FAILED"]
    exception: LoadExceptionObject
    tracks: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class VersionObject:
    string: str
    major: int
    minor: int
    patch: int


@dataclasses.dataclass
class GitObject:
    branch: str
    commit: str
    commitTime: int


@dataclasses.dataclass
class PluginObject:
    name: str
    version: str


@dataclasses.dataclass
class LavalinkInfoObject:
    version: VersionObject
    builtTime: int
    git: GitObject
    jvm: str
    lavaplayer: str
    sourceManagers: list[str]
    plugins: list[PluginObject]


@dataclasses.dataclass
class IPBlockObject:
    type: Literal["Inet4Address", "Inet6Address"]
    size: str


@dataclasses.dataclass
class FailingAddressObject:
    address: str
    failingTimestamp: int
    failingTimes: str


@dataclasses.dataclass
class RoutePlannerDetailObject:
    ipBlock: IPBlockObject
    failingAddresses: list[FailingAddressObject]
    rotateIndex: str
    ipIndex: str
    currentAddress: str
    currentAddressIndex: str
    blockIndex: str


@dataclasses.dataclass
class RoutePlannerStatusResponseObject:
    type: Literal[
        "RotatingIpRoutePlanner", "NanoIpRoutePlanner", "RotatingNanoIpRoutePlanner"
    ]  # replacement for class name
    details: RoutePlannerDetailObject


LavalinkLoadTrackObjects = Union[
    LavalinkTrackLoadedObject
    | LavalinkPlaylistLoadedObject
    | LavalinkNoMatchesObject
    | LavalinkLoadFailedObject
    | LavalinkSearchResultObject
]
