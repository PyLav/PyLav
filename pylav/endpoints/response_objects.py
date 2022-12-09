import dataclasses
import datetime
from typing import Annotated, Literal, Union

from packaging.version import Version
from packaging.version import parse as parse_version

from pylav.constants import SNAPSHOT_REGEX
from pylav.types import ValueRange


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackInfoObject:
    identifier: str
    isSeekable: bool
    author: str
    length: int = 0
    isStream: bool = False
    position: Union[int, None] = 0
    title: str = ""
    uri: Union[str, None] = None
    sourceName: Union[str, None] = None
    thumbnail: Union[str, None] = None
    isrc: Union[str, None] = None
    probeInfo: Union[str, None] = None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def to_database(self) -> dict:
        return {
            "identifier": self.identifier,
            "title": self.title,
            "uri": self.uri,
            "sourceName": self.sourceName,
            "isrc": self.isrc,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class PlaylistInfoObject:
    name: str = None
    selectedTrack: int = -1


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkTrackObject:
    info: Union[TrackInfoObject, dict]
    encoded: Union[str, None] = None
    track: Union[str, None] = None

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
    position: Union[int, None] = 0


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkOpObject:
    op: str = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkReadyOpObject(LavalinkOpObject):
    sessionId: str = None
    resumed: bool = False


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
    players: int = 0
    playingPlayers: int = 0
    uptime: int = 0
    memory: Union[LavalinkStatsMemoryObject, dict] = None
    cpu: Union[LavalinkStatCPUObject, dict] = None
    frameStats: Union[LavalinkStatsFrameStatsObject, dict, None] = None
    uptime_seconds: int = dataclasses.field(init=False)

    def __post_init__(self):
        if isinstance(self.memory, dict):
            object.__setattr__(self, "memory", LavalinkStatsMemoryObject(**self.memory))
        if isinstance(self.cpu, dict):
            object.__setattr__(self, "cpu", LavalinkStatCPUObject(**self.cpu))
        if isinstance(self.frameStats, dict):
            object.__setattr__(self, "frameStats", LavalinkStatsFrameStatsObject(**self.frameStats))
        object.__setattr__(self, "uptime_seconds", self.uptime / 1000)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkPlayerUpdateObject(LavalinkOpObject):
    guildId: str = None
    state: Union[PlayerStateObject, dict] = None

    def __post_init__(self):
        if isinstance(self.state, dict):
            object.__setattr__(self, "state", PlayerStateObject(**self.state))


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackStartEventOpObject(LavalinkOpObject):
    op: Literal["event"] = None
    guildId: str = None
    type: Literal["TrackStartEvent"] = None
    encodedTrack: str = None
    track: Union[str, None] = None

    def __post_init__(self):
        if self.encodedTrack is None:
            object.__setattr__(self, "encodedTrack", self.track)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackEndEventOpObject(LavalinkOpObject):
    op: Literal["event"] = None
    guildId: str = None
    type: Literal["TrackEndEvent"] = None
    reason: Literal["FINISHED", "LOAD_FAILED", "STOPPED", "REPLACED", "CLEANUP"] = None
    encodedTrack: str = None
    track: Union[str, None] = None

    def __post_init__(self):
        if self.encodedTrack is None:
            object.__setattr__(self, "encodedTrack", self.track)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LoadExceptionObject:
    severity: Literal["COMMON", "SUSPICIOUS", "FAULT"]
    message: Union[str, None] = None


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackExceptionObject(LoadExceptionObject):
    cause: str = None  # This is only optional so that inheritance in python works


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TrackExceptionEventOpObject:
    op: Literal["event"]
    guildId: str
    type: Literal["TrackExceptionEvent"]
    exception: Union[TrackExceptionObject, dict]
    encodedTrack: str = None
    track: Union[str, None] = None

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
    track: Union[str, None] = None

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
    segments: list[Union[SegmentObject, dict]]

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
    segment: Union[SegmentObject, dict]

    def __post_init__(self):
        if isinstance(self.segment, dict):
            object.__setattr__(self, "segment", SegmentObject(**self.segment))


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class VoiceStateObject:
    token: str
    endpoint: str
    sessionId: str
    connected: Union[bool, None] = None
    ping: Union[int, None] = -1

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "endpoint": self.endpoint,
            "sessionId": self.sessionId,
            "connected": self.connected,
            "ping": self.ping,
        }

    def __repr__(self):
        return f"<VoiceStateObject(token={'OBFUSCATED' if self.token else None} endpoint={self.endpoint} sessionId={self.sessionId} connected={self.connected} ping={self.ping})"


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class ValueRangeObject:
    min: float
    max: float

    def validate_value(self, x):
        if not (self.min <= x <= self.max):
            raise ValueError(f"{x} must be in range({self.min}, {self.max})")


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class EqualizerBandObject:
    band: Annotated[Union[int, None], ValueRange(min=0, max=14)]
    gain: Annotated[Union[float, None], ValueRange(min=-0.25, max=1.0)]

    def to_dict(self) -> dict:
        return {"band": self.band, "gain": self.gain}


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class KaraokeObject:
    level: Annotated[Union[float, None], ValueRange(min=0.0, max=1.0)] = None
    monoLevel: Annotated[Union[float, None], ValueRange(min=0.0, max=1.0)] = None
    filterBand: Union[float, None] = None
    filterWidth: Union[float, None] = None

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "monoLevel": self.monoLevel,
            "filterBand": self.filterBand,
            "filterWidth": self.filterWidth,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TimescaleObject:
    speed: Annotated[Union[float, None], ValueRange(min=0.0, max=float("inf"))] = None
    pitch: Annotated[Union[float, None], ValueRange(min=0.0, max=float("inf"))] = None
    rate: Annotated[Union[float, None], ValueRange(min=0.0, max=float("inf"))] = None

    def to_dict(self) -> dict:
        return {
            "speed": self.speed,
            "pitch": self.pitch,
            "rate": self.rate,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class TremoloObject:
    frequency: Annotated[Union[float, None], ValueRange(min=0.0, max=float("inf"))] = None
    depth: Annotated[Union[float, None], ValueRange(min=0.0, max=1.0)] = None

    def to_dict(self) -> dict:
        return {
            "frequency": self.frequency,
            "depth": self.depth,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class VibratoObject:
    frequency: Annotated[Union[float, None], ValueRange(min=0, max=14)] = None
    depth: Annotated[Union[float, None], ValueRange(min=0.0, max=1.0)] = None

    def to_dict(self) -> dict:
        return {
            "frequency": self.frequency,
            "depth": self.depth,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class RotationObject:
    rotationHz: Annotated[Union[float, None], ValueRange(min=0.0, max=float("inf"))] = None

    def to_dict(self) -> dict:
        return {"rotationHz": self.rotationHz}


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class DistortionObject:
    sinOffset: Union[float, None] = None
    sinScale: Union[float, None] = None
    cosOffset: Union[float, None] = None
    cosScale: Union[float, None] = None
    tanOffset: Union[float, None] = None
    tanScale: Union[float, None] = None
    offset: Union[float, None] = None
    scale: Union[float, None] = None

    def to_dict(self) -> dict:
        return {
            "sinOffset": self.sinOffset,
            "sinScale": self.sinScale,
            "cosOffset": self.cosOffset,
            "cosScale": self.cosScale,
            "tanOffset": self.tanOffset,
            "tanScale": self.tanScale,
            "offset": self.offset,
            "scale": self.scale,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class ChannelMixObject:
    leftToLeft: Annotated[Union[float, None], ValueRange(min=0.0, max=1.0)] = None
    leftToRight: Annotated[Union[float, None], ValueRange(min=0.0, max=1.0)] = None
    rightToLeft: Annotated[Union[float, None], ValueRange(min=0.0, max=1.0)] = None
    rightToRight: Annotated[Union[float, None], ValueRange(min=0.0, max=1.0)] = None

    def to_dict(self) -> dict:
        return {
            "leftToLeft": self.leftToLeft,
            "leftToRight": self.leftToRight,
            "rightToLeft": self.rightToLeft,
            "rightToRight": self.rightToRight,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LowPassObject:
    smoothing: Annotated[Union[float, None], ValueRange(min=1.0, max=float("inf"))] = None

    def to_dict(self) -> dict:
        return {"smoothing": self.smoothing}


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class EchoObject:
    delay: Annotated[Union[int, None], ValueRange(min=0, max=float("inf"))] = None
    decay: Annotated[Union[float, None], ValueRange(min=0.0, max=1.0)] = None

    def to_dict(self) -> dict:
        return {
            "delay": self.delay,
            "decay": self.decay,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class FiltersObject:
    volume: Union[float, None] = None
    equalizer: Union[list[Union[EqualizerBandObject, dict]], None] = dataclasses.field(default_factory=list)
    karaoke: Union[KaraokeObject, dict, None] = dataclasses.field(default_factory=dict)
    timescale: Union[TimescaleObject, dict, None] = dataclasses.field(default_factory=dict)
    tremolo: Union[TremoloObject, dict, None] = dataclasses.field(default_factory=dict)
    vibrato: Union[VibratoObject, dict, None] = dataclasses.field(default_factory=dict)
    rotation: Union[RotationObject, dict, None] = dataclasses.field(default_factory=dict)
    distortion: Union[DistortionObject, dict, None] = dataclasses.field(default_factory=dict)
    channelMix: Union[ChannelMixObject, dict, None] = dataclasses.field(default_factory=dict)
    lowPass: Union[LowPassObject, dict, None] = dataclasses.field(default_factory=dict)
    echo: Union[EchoObject, dict, None] = dataclasses.field(default_factory=dict)

    def __post_init__(self):
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

    def to_dict(self) -> dict:
        return {
            "volume": self.volume,
            "equalizer": [band.to_dict() if isinstance(band, EqualizerBandObject) else band for band in self.equalizer],
            "karaoke": self.karaoke.to_dict() if self.karaoke else None,
            "timescale": self.timescale.to_dict() if self.timescale else None,
            "tremolo": self.tremolo.to_dict() if self.tremolo else None,
            "vibrato": self.vibrato.to_dict() if self.vibrato else None,
            "rotation": self.rotation.to_dict() if self.rotation else None,
            "distortion": self.distortion.to_dict() if self.distortion else None,
            "channelMix": self.channelMix.to_dict() if self.channelMix else None,
            "lowPass": self.lowPass.to_dict() if self.lowPass else None,
            "echo": self.echo.to_dict() if self.echo else None,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkPlayerObject:
    guildId: str
    volume: int
    paused: bool
    voice: Union[VoiceStateObject, dict]
    filters: Union[FiltersObject, dict]
    track: Union[LavalinkTrackObject, dict, None] = None

    def __post_init__(self):
        if isinstance(self.voice, dict):
            object.__setattr__(self, "voice", VoiceStateObject(**self.voice))
        if isinstance(self.filters, dict):
            object.__setattr__(self, "filters", FiltersObject(**self.filters))
        if isinstance(self.track, dict):
            object.__setattr__(self, "track", LavalinkTrackObject(**self.track))

    def to_dict(self) -> dict:
        return {
            "guildId": self.guildId,
            "volume": self.volume,
            "paused": self.paused,
            "voice": self.voice.to_dict(),
            "filters": self.filters.to_dict(),
            "track": self.track.to_dict() if self.track else None,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkTrackLoadedObject:
    loadType: Literal["TRACK_LOADED"]
    playlistInfo: Union[PlaylistInfoObject, dict]
    tracks: list[Union[LavalinkTrackObject, dict]] = dataclasses.field(default_factory=list)

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
    playlistInfo: Union[PlaylistInfoObject, dict]
    tracks: list[Union[LavalinkTrackObject, dict]] = dataclasses.field(default_factory=list)

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
    playlistInfo: Union[PlaylistInfoObject, dict]
    tracks: list[Union[LavalinkTrackObject, dict]] = dataclasses.field(default_factory=list)

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
    playlistInfo: Union[PlaylistInfoObject, dict]
    tracks: list[Union[LavalinkTrackObject, dict]] = dataclasses.field(default_factory=list)

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
    exception: Union[LoadExceptionObject, dict]
    playlistInfo: Union[PlaylistInfoObject, dict]
    tracks: list[Union[LavalinkTrackObject, dict]] = dataclasses.field(default_factory=list)

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
    preRelease: Union[str, None] = None

    def __post_init__(self):
        if match := SNAPSHOT_REGEX.match(self.semver):
            version = Version(f"3.999.0-alpha+{match.group('commit')}")
        else:
            version = parse_version(self.semver)
        object.__setattr__(self, "semver", version)


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
    filters: list[str]
    plugins: Union[list[PluginObject], dict]

    def __post_init__(self):

        if isinstance(self.version, dict):
            object.__setattr__(self, "version", VersionObject(**self.version))
        if isinstance(self.git, dict):
            object.__setattr__(self, "git", GitObject(**self.git))
        temp = []
        for p in self.plugins.get("plugins", []):
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
    ipBlock: Union[IPBlockObject, dict]
    failingAddresses: list[Union[FailingAddressObject, dict]]
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
    type: Union[Literal["RotatingIpRoutePlanner", "NanoIpRoutePlanner", "RotatingNanoIpRoutePlanner"], None] = None
    details: Union[RoutePlannerDetailObject, dict, None] = None

    def __post_init__(self):
        if isinstance(self.details, dict):
            object.__setattr__(self, "details", RoutePlannerDetailObject(**self.details))


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class LavalinkErrorResponseObject:
    timestamp: int | datetime.datetime
    status: int
    error: str
    message: str
    path: str
    trace: Union[str, None] = None

    def __post_init__(self):
        if isinstance(self.timestamp, int):
            object.__setattr__(self, "timestamp", datetime.datetime.fromtimestamp(self.timestamp / 1000))

    def __bool__(self):
        return False


LavalinkLoadTrackObjects = Union[
    LavalinkTrackLoadedObject,
    LavalinkPlaylistLoadedObject,
    LavalinkNoMatchesObject,
    LavalinkLoadFailedObject,
    LavalinkSearchResultObject,
]
