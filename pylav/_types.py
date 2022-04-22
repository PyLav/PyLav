# isort: skip_file
from __future__ import annotations

from typing import Any, Awaitable, Callable, Coroutine, Literal, Optional, TYPE_CHECKING, TypeVar, Union
from typing_extensions import TypedDict

T = TypeVar("T")

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    from discord.ext.commands.bot import AutoShardedBot, Bot
    from discord.ext.commands.cog import Cog
    from discord.ext.commands.context import Context
    from discord.ext.commands.errors import CommandError

    try:
        from redbot.core.bot import Red
        from redbot.core.commands import Cog as RedCog
        from redbot.core.commands.context import Context as RedContext
    except ImportError:
        Red = AutoShardedBot
        RedCog = Cog
        RedContext = Context

    from pylav.utils import PyLavContext
    from pylav.client import Client

    P = ParamSpec("P")
    MaybeAwaitableFunc = Callable[P, "MaybeAwaitable[T]"]
else:
    try:
        from redbot.core.bot import Red as BotClient
    except ImportError:
        from discord.ext.commands.bot import AutoShardedBot as BotClient

    P = TypeVar("P")
    MaybeAwaitableFunc = tuple[P, T]

_Bot = Union["BotClientWithLavalink", "Red", "Bot", "AutoShardedBot"]


class BotClientWithLavalink(BotClient):
    lavalink: Client
    _pylav_client: Client


Coro = Coroutine[Any, Any, T]
CoroFunc = Callable[..., Coro[Any]]
MaybeCoro = Union[T, Coro[T]]
MaybeAwaitable = Union[T, Awaitable[T]]

CogT = TypeVar("CogT", bound="Optional[Union[RedCog, Cog]]")
Check = Callable[["ContextT"], MaybeCoro[bool]]
Hook = Union[Callable[["CogT", "ContextT"], Coro[Any]], Callable[["ContextT"], Coro[Any]]]
Error = Union[
    Callable[["CogT", "ContextT", "CommandError"], Coro[Any]],
    Callable[["ContextT", "CommandError"], Coro[Any]],
]

ContextT = TypeVar("ContextT", bound="Union[PyLavContext[Any], RedContext[Any], Context[Any]]")
BotT = TypeVar("BotT", bound=Union[BotClientWithLavalink, _Bot], covariant=True)


class playlistInfoT(TypedDict):
    name: str
    selectedTrack: int


class TrackInfoT(TypedDict):
    identifier: str
    isSeekable: bool
    author: str
    length: int
    title: str
    uri: str
    position: int | None
    isStream: bool
    source: str | None


class TrackT(TypedDict):
    track: str
    info: TrackInfoT


class LavalinkResponseT(TypedDict):
    loadType: Literal["TRACK_LOADED", "PLAYLIST_LOADED", "SEARCH_RESULT", "NO_MATCHES", "LOAD_FAILED"]
    playlistInfo: playlistInfoT
    tracks: list[TrackT]


# This is merely a tag type to avoid circular import issues.
# Yes, this is a terrible solution but ultimately it is the only solution.
class _BaseCommand:
    __slots__ = ()
