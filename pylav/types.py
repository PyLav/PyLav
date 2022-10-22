from __future__ import annotations

from abc import ABC
from collections.abc import Awaitable, Coroutine
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, Callable, Literal, TypedDict, TypeVar, Union

import discord
from typing_extensions import NotRequired

if TYPE_CHECKING:
    from discord import app_commands
    from discord.ext.commands import AutoShardedBot, Bot, Cog, Context

    try:
        from redbot.core.bot import Red
        from redbot.core.bot import Red as BotClient
        from redbot.core.commands import Cog as RedCog
        from redbot.core.commands import Context as RedContext
    except ImportError:
        BotClient = Red = AutoShardedBot
        RedCog = Cog
        RedContext = Context

    from pylav.client import Client
    from pylav.query import Query
    from pylav.utils import PyLavContext

else:
    try:
        from redbot.core import commands
        from redbot.core.bot import Red as BotClient
    except ImportError:
        from discord.ext import commands
        from discord.ext.commands import AutoShardedBot as BotClient


_Bot = Union["Red", "Bot", "AutoShardedBot"]


class PyLavCogMixin(ABC):
    __version__: str
    bot: BotT
    lavalink: Client
    pylav: Client

    @commands.command()
    async def command_play(self, context: PyLavContext, *, query: str = None):
        ...


T = TypeVar("T")
Coro = Coroutine[Any, Any, T]
CoroFunc = Callable[..., Coro[Any]]
MaybeCoro = Union[T, Coro[T]]
MaybeAwaitable = Union[T, Awaitable[T]]

CogT = TypeVar("CogT", bound="Optional[Union[PyLavCogMixin, RedCog, Cog]]")
Check = Callable[["ContextT"], MaybeCoro[bool]]
Hook = Union[Callable[["CogT", "ContextT"], Coro[Any]], Callable[["ContextT"], Coro[Any]]]
Error = Union[
    Callable[["CogT", "ContextT", "CommandError"], Coro[Any]],
    Callable[["ContextT", "CommandError"], Coro[Any]],
]

ContextT = TypeVar("ContextT", bound="Union[PyLavContext[Any], RedContext[Any], Context[Any]]")


class BotClientWithLavalink(BotClient):
    _pylav_client: Client
    lavalink: Client
    pylav: Client

    async def get_context(
        self, message: discord.abc.Message | InteractionT, *, cls: type[PyLavContext] = None  # noqa: F821
    ) -> PyLavContext[Any]:
        ...


class _InteractionT(discord.Interaction):
    client: BotClientWithLavalink
    response: discord.InteractionResponse
    followup: discord.Webhook
    command: app_commands.Command[Any, ..., Any] | app_commands.ContextMenu | None
    channel: discord.interactions.InteractionChannel | None


BotT = TypeVar("BotT", bound=BotClientWithLavalink, covariant=True)
InteractionT = TypeVar("InteractionT", bound="Union[_InteractionT, discord.Interaction]")
ContextObjectT = TypeVar("ContextObjectT", bound="Union[PyLavContext[Any], InteractionT[Any], Context[Any]]")

QueryT = TypeVar("QueryT", bound="Type[Query]")


class TimedFeatureT(TypedDict):
    enabled: bool
    time: int


class PlaylistInfoT(TypedDict):  # noqa
    name: str
    selectedTrack: int


class TrackInfoT(TypedDict):
    identifier: str
    isSeekable: bool
    author: str
    length: int
    title: str
    isStream: bool
    uri: str | None
    position: int | None
    sourceName: str | None
    source: NotRequired[str | None]


class TrackT(TypedDict):
    encoded: str
    track: NotRequired[str]
    info: TrackInfoT


class PlayerStateT(TypedDict):
    time: int
    position: NotRequired[int]
    connected: bool
    ping: int


class LavalinkOpT(TypedDict):
    op: str


class LavalinkReadyT(LavalinkOpT):
    resumed: NotRequired[bool]
    sessionId: str


class LavalinkStatCPUT(TypedDict):
    cores: int
    systemLoad: float
    lavalinkLoad: float


class LavalinkStatsMemoryT(TypedDict):
    free: int
    allocated: int
    reservable: int
    used: int


class LavalinkStatsFrameStatsT(TypedDict):
    sent: int
    nulled: int
    deficit: int


class LavalinkStatsT(LavalinkOpT):
    players: int
    playingPlayers: int
    uptime: int
    memory: LavalinkStatsMemoryT
    cpu: LavalinkStatCPUT
    frameStats: LavalinkStatsFrameStatsT


class LavalinkPlayerUpdateT(LavalinkOpT):
    guildId: str
    state: PlayerStateT


class TrackStartEventT(TypedDict):
    op: Literal["event"]
    guildId: str
    type: Literal["TrackStartEvent"]
    encodedTrack: str
    track: NotRequired[str]


class TrackEndEventT(TypedDict):
    op: Literal["event"]
    guildId: str
    type: Literal["TrackEndEvent"]
    encodedTrack: str
    track: NotRequired[str]
    reason: Literal["FINISHED", "LOAD_FAILED", "STOPPED", "REPLACED", "CLEANUP"]


class LoadExceptionT(TypedDict):
    message: str
    severity: Literal["COMMON", "SUSPICIOUS", "FAULT"]


class TrackExceptionT(LoadExceptionT):
    cause: str


class TrackExceptionEventT(TypedDict):
    op: Literal["event"]
    guildId: str
    type: Literal["TrackExceptionEvent"]
    encodedTrack: str
    track: NotRequired[str]
    exception: TrackExceptionT


class TrackStuckEventT(TypedDict):
    op: Literal["event"]
    guildId: str
    type: Literal["TrackStuckEvent"]
    encodedTrack: str
    track: NotRequired[str]
    thresholdMs: int


class WebSocketClosedEventT(TypedDict):
    op: Literal["event"]
    guildId: str
    type: Literal["WebSocketClosedEvent"]
    code: int
    reason: str
    byRemote: bool


class SegmentT(TypedDict):
    category: str
    start: str
    end: str


class SegmentsLoadedEventT(TypedDict):
    op: Literal["event"]
    guildId: str
    type: Literal["SegmentsLoadedEvent"]
    segments: list[SegmentT]


class SegmentSkippedT(TypedDict):
    op: Literal["event"]
    guildId: str
    type: Literal["SegmentSkippedEvent"]
    segment: SegmentT


LavalinkEventT = Union[
    TrackStartEventT,
    TrackEndEventT,
    TrackExceptionEventT,
    TrackStuckEventT,
    WebSocketClosedEventT,
    SegmentsLoadedEventT,
    SegmentSkippedT,
]


class VoiceStateT(TypedDict):
    token: str
    endpoint: str
    sessionId: str
    connected: NotRequired[bool]
    ping: NotRequired[int]


@dataclass
class ValueRange:
    min: float
    max: float

    def validate_value(self, x):
        if not (self.min <= x <= self.max):
            raise ValueError(f"{x} must be in range({self.min}, {self.max})")


class EqualizerBandT(TypedDict):
    band: Annotated[int, ValueRange(min=0, max=14)]
    gain: Annotated[float, ValueRange(min=-0.25, max=1.0)]


EqualizerT = TypeVar("EqualizerT", bound="Type[List[EqualizerBandT]]")


class KaraokeT(TypedDict):
    level: NotRequired[Annotated[float, ValueRange(min=0.0, max=1.0)]]
    monoLevel: NotRequired[Annotated[float, ValueRange(min=0.0, max=1.0)]]
    filterBand: NotRequired[float]
    filterWidth: NotRequired[float]


class TimescaleT(TypedDict):
    speed: NotRequired[Annotated[float, ValueRange(min=0.0, max=float("inf"))]]
    pitch: NotRequired[Annotated[float, ValueRange(min=0.0, max=float("inf"))]]
    rate: NotRequired[Annotated[float, ValueRange(min=0.0, max=float("inf"))]]


class TremoloT(TypedDict):
    frequency: NotRequired[Annotated[float, ValueRange(min=0.0, max=float("inf"))]]
    depth: NotRequired[Annotated[float, ValueRange(min=0.0, max=1.0)]]


class VibratoT(TypedDict):
    frequency: NotRequired[Annotated[float, ValueRange(min=0, max=14)]]
    depth: NotRequired[Annotated[float, ValueRange(min=0.0, max=1.0)]]


class RotationT(TypedDict):
    rotationHz: NotRequired[Annotated[float, ValueRange(min=0.0, max=float("inf"))]]


class DistortionT(TypedDict):
    sinOffset: NotRequired[float]
    sinScale: NotRequired[float]
    cosOffset: NotRequired[float]
    cosScale: NotRequired[float]
    tanOffset: NotRequired[float]
    tanScale: NotRequired[float]
    offset: NotRequired[float]
    scale: NotRequired[float]


class ChannelMixT(TypedDict):
    leftToLeft: NotRequired[Annotated[float, ValueRange(min=0.0, max=1.0)]]
    leftToRight: NotRequired[Annotated[float, ValueRange(min=0.0, max=1.0)]]
    rightToLeft: NotRequired[Annotated[float, ValueRange(min=0.0, max=1.0)]]
    rightToRight: NotRequired[Annotated[float, ValueRange(min=0.0, max=1.0)]]


class LowPassT(TypedDict):
    smoothing: NotRequired[Annotated[float, ValueRange(min=1.0, max=float("inf"))]]


class EchoT(TypedDict):
    delay: NotRequired[Annotated[int, ValueRange(min=0, max=float("inf"))]]
    decay: NotRequired[Annotated[float, ValueRange(min=0.0, max=1.0)]]


class FiltersT(TypedDict):
    volume: NotRequired[float]
    equalizer: NotRequired[EqualizerT]
    karaoke: NotRequired[KaraokeT]
    timescale: NotRequired[TimescaleT]
    tremolo: NotRequired[TremoloT]
    vibrato: NotRequired[VibratoT]
    rotation: NotRequired[RotationT]
    distortion: NotRequired[DistortionT]
    channelMix: NotRequired[ChannelMixT]
    lowPass: NotRequired[LowPassT]
    echo: NotRequired[EchoT]


class LavalinkPlayerT(TypedDict):
    guildId: str
    track: TrackT | None
    volume: int
    paused: bool
    voice: VoiceStateT
    filters: FiltersT


RestGetPlayersResponseT = TypeVar("RestGetPlayersResponseT", bound="Type[List[LavalinkPlayerT]]")
RestGetPlayerResponseT = TypeVar("RestGetPlayerResponseT", bound="Type[LavalinkPlayerT]")


class RestPatchPlayerParamsT(TypedDict):
    noReplace: NotRequired[bool]


class RestPatchPlayerPayloadT(TypedDict):
    encodedTrack: NotRequired[str]
    identifier: NotRequired[str]
    position: NotRequired[int]
    endTime: NotRequired[int]
    volume: NotRequired[int]
    paused: NotRequired[bool]
    filters: NotRequired[FiltersT]
    voice: NotRequired[VoiceStateT]


RestPatchPlayerResponseT = TypeVar("RestPatchPlayerResponseT", bound="Type[LavalinkPlayerT]")


class RestPatchSessionPayloadT(TypedDict):
    resumingKey: str
    timeout: int


class TrackLoadedT(TypedDict):
    loadType: Literal["TRACK_LOADED"]
    tracks: list[TrackT]


class PlaylistLoadedT(TypedDict):
    loadType: Literal["PLAYLIST_LOADED"]
    playlistInfo: PlaylistInfoT
    tracks: list[TrackT]


class SearchResultT(TypedDict):
    loadType: Literal["SEARCH_RESULT"]
    tracks: list[TrackT]


class NoMatchesT(TypedDict):
    loadType: Literal["NO_MATCHES"]


class LoadFailedT(TypedDict):
    loadType: Literal["LOAD_FAILED"]
    exception: LoadExceptionT


LavalinkResponseT = Union[TrackLoadedT, PlaylistLoadedT, SearchResultT, NoMatchesT, LoadFailedT]
LoadTracksResponseT = TypeVar("LoadTracksResponseT", bound="Type[LavalinkResponseT]")


class RestGetLoadTrackParamsT(TypedDict):
    identifier: str


class RestGetDecodeTrackParamsT(TypedDict):
    track: str


RestGetDecodeTrackResponseT = TypeVar("RestGetDecodeTrackResponseT", bound="Type[TrackT]")


class RestPostDecodeTracksPayloadT(TypedDict):
    tracks: list[str]


RestPostDecodeTracksResponseT = TypeVar("RestPostDecodeTracksResponseT", bound="Type[List[TrackT]]")


class VersionT(TypedDict):
    string: str
    major: int
    minor: int
    patch: int


class GitT(TypedDict):
    branch: str
    commit: str
    commitTime: int


class PluginT(TypedDict):
    name: str
    version: str


class RestGetInfoResponseT(TypedDict):
    version: VersionT
    builtTime: int
    git: GitT
    jvm: str
    lavaplayer: str
    sourceManagers: list[str]
    plugins: list[PluginT]


RestGetStatsResponseT = TypeVar("RestGetStatsResponseT", bound="Type[StatsT]")

DeprecatedRestGetPluginsResponseT = TypeVar("DeprecatedRestGetPluginsResponseT", bound="Type[List[PluginT]]")
DeprecatedRestGetVersionResponseT = TypeVar("DeprecatedRestGetVersionResponseT", bound="Type[str]")

# TODO:
#  1: Add the rest of the RoutePlanner endpoints types
#  2: Typing the payloads, responses and params for Resuming Lavalink Sessions rest calls


class IPBlockT(TypedDict):
    type: Literal["Inet4Address", "Inet6Address"]
    size: str


class FailingAddressT(TypedDict):
    address: str
    failingTimestamp: int
    failingTimes: str


class RoutePlannerDetailT(TypedDict):
    ipBlock: IPBlockT
    failingAddresses: list[FailingAddressT]
    rotateIndex: str
    ipIndex: str
    currentAddress: str
    currentAddressIndex: str
    blockIndex: str


class RoutePlannerStatusResponseT(TypedDict):
    type: Literal[
        "RotatingIpRoutePlanner", "NanoIpRoutePlanner", "RotatingNanoIpRoutePlanner"
    ]  # replacement for class name
    details: RoutePlannerDetailT
