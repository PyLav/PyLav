import dataclasses
from typing import Annotated, Literal, Union

from pylav.types import ValueRange


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackInfoObject:
    identifier: str
    isSeekable: bool
    author: str
    length: int = 0
    isStream: bool = False
    position: int | None = 0
    title: str = ""
    uri: str | None = None
    sourceName: str | None = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class PlaylistInfoObject:
    name: str
    selectedTrack: int = -1


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkTrackObject:
    info: TrackInfoObject | dict
    encoded: str | None = None
    track: str | None = None

    def __post_init__(self):
        if self.encoded is None:
            object.__setattr__(self, "encoded", self.track)
        if isinstance(self.info, dict):
            object.__setattr__(self, "info", TrackInfoObject(**self.info))

    def to_dict(self):
        return {
            "info": dataclasses.asdict(self.info),
            "encoded": self.encoded,
            "track": self.track,
        }


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
    memory: LavalinkStatsMemoryObject | dict
    cpu: LavalinkStatCPUObject | dict
    frameStats: LavalinkStatsFrameStatsObject | dict | None = None

    def __post_init__(self):
        if isinstance(self.memory, dict):
            object.__setattr__(self, "memory", LavalinkStatsMemoryObject(**self.memory))
        if isinstance(self.cpu, dict):
            object.__setattr__(self, "cpu", LavalinkStatCPUObject(**self.cpu))
        if isinstance(self.frameStats, dict):
            object.__setattr__(self, "frameStats", LavalinkStatsFrameStatsObject(**self.frameStats))


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkPlayerUpdateObject(LavalinkOpObject):
    guildId: str
    state: PlayerStateObject | dict

    def __post_init__(self):
        if isinstance(self.state, dict):
            object.__setattr__(self, "state", PlayerStateObject(**self.state))


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
    exception: TrackExceptionObject | dict
    encodedTrack: str = None
    track: str | None = None

    def __post_init__(self):
        if self.encodedTrack is None:
            object.__setattr__(self, "encodedTrack", self.track)
        if isinstance(self.exception, dict):
            object.__setattr__(self, "exception", TrackExceptionObject(**self.exception))


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
    code: int = None
    reason: str = None
    byRemote: bool = False


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
    segments: list[SegmentObject | dict]

    def __post_init__(self):
        temp = []
        for s in self.segments:
            if isinstance(s, SegmentObject) or (isinstance(s, dict) and (s := SegmentObject(**s))):
                temp.append(s)
        object.__setattr__(self, "segments", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class SegmentSkippedEventOpObject:
    op: Literal["event"]
    guildId: str
    type: Literal["SegmentSkippedEvent"]
    segment: SegmentObject | dict

    def __post_init__(self):
        if isinstance(self.segment, dict):
            object.__setattr__(self, "segment", SegmentObject(**self.segment))


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
    equalizer: list[EqualizerBandObject | dict] | None = dataclasses.field(default_factory=list)
    karaoke: KaraokeObject | dict | None = dataclasses.field(default_factory=dict)
    timescale: TimescaleObject | dict | None = dataclasses.field(default_factory=dict)
    tremolo: TremoloObject | dict | None = dataclasses.field(default_factory=dict)
    vibrato: VibratoObject | dict | None = dataclasses.field(default_factory=dict)
    rotation: RotationObject | dict | None = dataclasses.field(default_factory=dict)
    distortion: DistortionObject | dict | None = dataclasses.field(default_factory=dict)
    channelMix: ChannelMixObject | dict | None = dataclasses.field(default_factory=dict)
    lowPass: LowPassObject | dict | None = dataclasses.field(default_factory=dict)
    echo: EchoObject | dict | None = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.equalizer, list):
            object.__setattr__(
                self, "equalizer", [EqualizerBandObject(**band) for band in self.equalizer] if self.equalizer else None
            )
        if isinstance(self.karaoke, dict):
            object.__setattr__(self, "karaoke", KaraokeObject(**self.karaoke) if self.karaoke else None)
        if isinstance(self.timescale, dict):
            object.__setattr__(self, "timescale", TimescaleObject(**self.timescale) if self.timescale else None)
        if isinstance(self.tremolo, dict):
            object.__setattr__(self, "tremolo", TremoloObject(**self.tremolo) if self.tremolo else None)
        if isinstance(self.vibrato, dict):
            object.__setattr__(self, "vibrato", VibratoObject(**self.vibrato) if self.vibrato else None)
        if isinstance(self.rotation, dict):
            object.__setattr__(self, "rotation", RotationObject(**self.rotation) if self.rotation else None)
        if isinstance(self.distortion, dict):
            object.__setattr__(self, "distortion", DistortionObject(**self.distortion) if self.distortion else None)
        if isinstance(self.channelMix, dict):
            object.__setattr__(self, "channelMix", ChannelMixObject(**self.channelMix) if self.channelMix else None)
        if isinstance(self.lowPass, dict):
            object.__setattr__(self, "lowPass", LowPassObject(**self.lowPass) if self.lowPass else None)
        if isinstance(self.echo, dict):
            object.__setattr__(self, "echo", EchoObject(**self.echo) if self.echo else None)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkPlayerObject:
    guildId: str
    volume: int
    paused: bool
    voice: VoiceStateObject | dict
    filters: FiltersObject | dict | None = None
    track: LavalinkTrackObject | dict | None = None

    def __post_init__(self):
        if isinstance(self.voice, dict):
            object.__setattr__(self, "voice", VoiceStateObject(**self.voice))
        if isinstance(self.filters, dict):
            object.__setattr__(self, "filters", FiltersObject(**self.filters))
        if isinstance(self.track, dict):
            object.__setattr__(self, "track", LavalinkTrackObject(**self.track))


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkTrackLoadedObject:
    loadType: Literal["TRACK_LOADED"]
    playlistInfo: PlaylistInfoObject | dict
    tracks: list[LavalinkTrackObject | dict] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.playlistInfo, dict):
            object.__setattr__(self, "playlistInfo", PlaylistInfoObject(**self.playlistInfo))
        temp = []
        for t in self.tracks:
            if isinstance(t, LavalinkTrackObject) or (isinstance(t, dict) and (t := LavalinkTrackObject(**t))):
                temp.append(t)
        object.__setattr__(self, "tracks", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkPlaylistLoadedObject:
    loadType: Literal["PLAYLIST_LOADED"]
    playlistInfo: PlaylistInfoObject | dict
    tracks: list[LavalinkTrackObject | dict] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.playlistInfo, dict):
            object.__setattr__(self, "playlistInfo", PlaylistInfoObject(**self.playlistInfo))
        temp = []
        for t in self.tracks:
            if isinstance(t, LavalinkTrackObject) or (isinstance(t, dict) and (t := LavalinkTrackObject(**t))):
                temp.append(t)
        object.__setattr__(self, "tracks", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkSearchResultObject:
    loadType: Literal["SEARCH_RESULT"]
    playlistInfo: PlaylistInfoObject | dict
    tracks: list[LavalinkTrackObject | dict] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.playlistInfo, dict):
            object.__setattr__(self, "playlistInfo", PlaylistInfoObject(**self.playlistInfo))
        temp = []
        for t in self.tracks:
            if isinstance(t, LavalinkTrackObject) or (isinstance(t, dict) and (t := LavalinkTrackObject(**t))):
                temp.append(t)
        object.__setattr__(self, "tracks", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkNoMatchesObject:
    loadType: Literal["NO_MATCHES"]
    playlistInfo: PlaylistInfoObject | dict
    tracks: list[LavalinkTrackObject | dict] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.playlistInfo, dict):
            object.__setattr__(self, "playlistInfo", PlaylistInfoObject(**self.playlistInfo))
        temp = []
        for t in self.tracks:
            if isinstance(t, LavalinkTrackObject) or (isinstance(t, dict) and (t := LavalinkTrackObject(**t))):
                temp.append(t)
        object.__setattr__(self, "tracks", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkLoadFailedObject:
    loadType: Literal["LOAD_FAILED"]
    exception: LoadExceptionObject | dict
    playlistInfo: PlaylistInfoObject | dict
    tracks: list[LavalinkTrackObject | dict] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.playlistInfo, dict):
            object.__setattr__(self, "playlistInfo", PlaylistInfoObject(**self.playlistInfo))
        temp = []
        for t in self.tracks:
            if isinstance(t, LavalinkTrackObject) or (isinstance(t, dict) and (t := LavalinkTrackObject(**t))):
                temp.append(t)
        object.__setattr__(self, "tracks", temp)


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

    def __post_init__(self):

        if isinstance(self.version, dict):
            object.__setattr__(self, "version", VersionObject(**self.version))
        if isinstance(self.git, dict):
            object.__setattr__(self, "git", GitObject(**self.git))
        temp = []
        for p in self.plugins:
            if isinstance(p, PluginObject) or (isinstance(p, dict) and (p := PluginObject(**p))):
                temp.append(p)
        object.__setattr__(self, "plugins", temp)


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
    ipBlock: IPBlockObject | dict
    failingAddresses: list[FailingAddressObject | dict]
    rotateIndex: str
    ipIndex: str
    currentAddress: str
    currentAddressIndex: str
    blockIndex: str

    def __post_init__(self):
        if isinstance(self.ipBlock, dict):
            object.__setattr__(self, "ipBlock", IPBlockObject(**self.ipBlock))
        temp = []
        for f in self.failingAddresses:
            if isinstance(f, FailingAddressObject) or (isinstance(f, dict) and (f := FailingAddressObject(**f))):
                temp.append(f)
        object.__setattr__(self, "failingAddresses", temp)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class RoutePlannerStatusResponseObject:
    type: Literal["RotatingIpRoutePlanner", "NanoIpRoutePlanner", "RotatingNanoIpRoutePlanner"] | None = None
    details: RoutePlannerDetailObject | dict | None = None

    def __post_init__(self):
        if isinstance(self.details, dict):
            object.__setattr__(self, "details", RoutePlannerDetailObject(**self.details))


LavalinkLoadTrackObjects = Union[
    LavalinkTrackLoadedObject
    | LavalinkPlaylistLoadedObject
    | LavalinkNoMatchesObject
    | LavalinkLoadFailedObject
    | LavalinkSearchResultObject
]
