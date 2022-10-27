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
    encoded: str | None = None
    track: str | None = None

    def __post_init__(self):
        if self.encoded is None:
            self.encoded = self.track


@dataclasses.dataclass
class PlayerStateObject:
    time: int = 0
    connected: bool = False
    ping: int = -1
    position: int | None = 0


@dataclasses.dataclass
class LavalinkOpObject:
    op: str


@dataclasses.dataclass
class LavalinkReadyOpObject(LavalinkOpObject):
    sessionId: str
    resumed: bool | None = False


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
    frameStats: LavalinkStatsFrameStatsObject | None = None


@dataclasses.dataclass
class LavalinkPlayerUpdateObject(LavalinkOpObject):
    guildId: str
    state: PlayerStateObject


@dataclasses.dataclass
class TrackStartEventOpObject(LavalinkOpObject):
    op: Literal["event"]
    guildId: str
    type: Literal["TrackStartEvent"]
    encodedTrack: str
    track: str | None = None


@dataclasses.dataclass
class TrackEndEventOpObject(LavalinkOpObject):
    op: Literal["event"]
    guildId: str
    type: Literal["TrackEndEvent"]
    reason: Literal["FINISHED", "LOAD_FAILED", "STOPPED", "REPLACED", "CLEANUP"]
    encodedTrack: str
    track: str | None = None


@dataclasses.dataclass
class LoadExceptionObject:
    severity: Literal["COMMON", "SUSPICIOUS", "FAULT"]
    message: str | None = None


@dataclasses.dataclass
class TrackExceptionObject(LoadExceptionObject):
    cause: str = None  # This is only optional so that inheritance in python works


@dataclasses.dataclass
class TrackExceptionEventOpObject:
    op: Literal["event"]
    guildId: str
    type: Literal["TrackExceptionEvent"]
    exception: TrackExceptionObject
    encodedTrack: str
    track: str | None = None


@dataclasses.dataclass
class TrackStuckEventOpObject:
    op: Literal["event"]
    guildId: str
    type: Literal["TrackStuckEvent"]
    thresholdMs: int
    encodedTrack: str
    track: str | None = None


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
    connected: bool | None = None
    ping: int | None = None


@dataclasses.dataclass
class ValueRangeObject:
    min: float
    max: float

    def validate_value(self, x):
        if not (self.min <= x <= self.max):
            raise ValueError(f"{x} must be in range({self.min}, {self.max})")


@dataclasses.dataclass
class EqualizerBandObject:
    band: Annotated[int | None, ValueRange(min=0, max=14)]
    gain: Annotated[float | None, ValueRange(min=-0.25, max=1.0)]


@dataclasses.dataclass
class KaraokeObject:
    level: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    monoLevel: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    filterBand: float | None = None
    filterWidth: float | None = None


@dataclasses.dataclass
class TimescaleObject:
    speed: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None
    pitch: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None
    rate: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None


@dataclasses.dataclass
class TremoloObject:
    frequency: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None
    depth: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass
class VibratoObject:
    frequency: Annotated[float | None, ValueRange(min=0, max=14)] = None
    depth: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass
class RotationObject:
    rotationHz: Annotated[float | None, ValueRange(min=0.0, max=float("inf"))] = None


@dataclasses.dataclass
class DistortionObject:
    sinOffset: float | None = None
    sinScale: float | None = None
    cosOffset: float | None = None
    cosScale: float | None = None
    tanOffset: float | None = None
    tanScale: float | None = None
    offset: float | None = None
    scale: float | None = None


@dataclasses.dataclass
class ChannelMixObject:
    leftToLeft: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    leftToRight: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    rightToLeft: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    rightToRight: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass
class LowPassObject:
    smoothing: Annotated[float | None, ValueRange(min=1.0, max=float("inf"))] = None


@dataclasses.dataclass
class EchoObject:
    delay: Annotated[int | None, ValueRange(min=0, max=float("inf"))] = None
    decay: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None


@dataclasses.dataclass
class FiltersObject:
    volume: float = None
    equalizer: list[EqualizerBandObject] = dataclasses.field(default_factory=list)
    karaoke: KaraokeObject | dict = dataclasses.field(default_factory=dict)
    timescale: TimescaleObject | dict = dataclasses.field(default_factory=dict)
    tremolo: TremoloObject | dict = dataclasses.field(default_factory=dict)
    vibrato: VibratoObject | dict = dataclasses.field(default_factory=dict)
    rotation: RotationObject | dict = dataclasses.field(default_factory=dict)
    distortion: DistortionObject | dict = dataclasses.field(default_factory=dict)
    channelMix: ChannelMixObject | dict = dataclasses.field(default_factory=dict)
    lowPass: LowPassObject | dict = dataclasses.field(default_factory=dict)
    echo: EchoObject | dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class LavalinkPlayerObject:
    guildId: str
    volume: int
    paused: bool
    voice: VoiceStateObject
    filters: FiltersObject
    track: LavalinkTrackObject | None = None


@dataclasses.dataclass
class LavalinkTrackLoadedObject:
    loadType: Literal["TRACK_LOADED"]
    playlistInfo: PlaylistInfoObject | dict = dataclasses.field(default_factory=dict)
    tracks: list[LavalinkTrackObject] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class LavalinkPlaylistLoadedObject:
    loadType: Literal["PLAYLIST_LOADED"]
    playlistInfo: PlaylistInfoObject | dict = dataclasses.field(default_factory=dict)
    tracks: list[LavalinkTrackObject] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class LavalinkSearchResultObject:
    loadType: Literal["SEARCH_RESULT"]
    playlistInfo: PlaylistInfoObject | dict = dataclasses.field(default_factory=dict)
    tracks: list[LavalinkTrackObject] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class LavalinkNoMatchesObject:
    loadType: Literal["NO_MATCHES"]
    playlistInfo: PlaylistInfoObject | dict = dataclasses.field(default_factory=dict)
    tracks: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class LavalinkLoadFailedObject:
    loadType: Literal["LOAD_FAILED"]
    exception: LoadExceptionObject
    playlistInfo: PlaylistInfoObject | dict = dataclasses.field(default_factory=dict)
    tracks: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class VersionObject:
    semver: str
    major: int
    minor: int
    patch: int
    preRelease: str | None = None


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
    buildTime: int
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
    type: Literal["RotatingIpRoutePlanner", "NanoIpRoutePlanner", "RotatingNanoIpRoutePlanner"] | None = None
    details: RoutePlannerDetailObject | None = None


LavalinkLoadTrackObjects = Union[
    LavalinkTrackLoadedObject
    | LavalinkPlaylistLoadedObject
    | LavalinkNoMatchesObject
    | LavalinkLoadFailedObject
    | LavalinkSearchResultObject
]
