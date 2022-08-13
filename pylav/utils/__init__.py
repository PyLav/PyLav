from __future__ import annotations

import asyncio
import collections
import contextlib
import dataclasses
import datetime
import functools
import random
import threading
import time
from asyncio import QueueFull, events, locks
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Generator, Iterable, Iterator
from copy import copy
from enum import Enum
from itertools import chain
from types import GenericAlias
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, TypeVar, Union

import discord  # type: ignore
from discord.backoff import ExponentialBackoff
from discord.ext import commands as dpy_command
from discord.ext.commands.view import StringView
from discord.types.embed import EmbedType
from discord.utils import MISSING as D_MISSING  # noqa
from discord.utils import maybe_coroutine

from pylav.types import BotT, CogT, ContextT, InteractionT

try:
    from redbot.core.commands import Command
    from redbot.core.commands import Context as _OriginalContextClass
except ImportError:
    from discord.ext.commands import Command
    from discord.ext.commands import Context as _OriginalContextClass

from discord.ext.commands import Context as DpyContext

if TYPE_CHECKING:
    from pylav import Player

__all__ = (
    "MISSING",
    "AsyncIter",
    "add_property",
    "format_time",
    "get_time_string",
    "PlayerQueue",
    "TrackHistoryQueue",
    "SegmentCategory",
    "Segment",
    "_process_commands",
    "_get_context",
    "PyLavContext",
    "ExponentialBackoffWithReset",
)

from pylav._logging import getLogger

T = TypeVar("T")

LOGGER = getLogger("PyLav.utils")
_RED_LOGGER = getLogger("red")

_LOCK = threading.Lock()


def _synchronized(lock):
    """Synchronization decorator"""

    def wrapper(f):
        @functools.wraps(f)
        def inner_wrapper(*args, **kw):
            with lock:
                return f(*args, **kw)

        return inner_wrapper

    return wrapper


class SingletonMethods:
    _has_run = {}
    _responses = {}

    @classmethod
    @_synchronized(_LOCK)
    def reset(cls):
        cls._has_run = {}
        cls._responses = {}

    @classmethod
    @_synchronized(_LOCK)
    def run_once(cls, f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not cls._has_run.get(f, False):
                cls._has_run[f] = True
                output = f(*args, **kwargs)
                cls._responses[f] = output
                return output
            else:
                return cls._responses.get(f, None)

        cls._has_run[f] = False
        return wrapper

    @classmethod
    @_synchronized(_LOCK)
    def run_once_async(cls, f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not cls._has_run.get(f, False):
                cls._has_run[f.__name__] = True
                return f(*args, **kwargs)
            else:
                return asyncio.sleep(0)

        cls._has_run[f] = False
        return wrapper


class _Singleton(type):
    _instances = {}

    def __call__(self, *args, **kwargs):
        if self not in self._instances:
            self._locked_call(*args, **kwargs)
        return self._instances[self]

    @_synchronized(_LOCK)
    def _locked_call(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)


class MissingSentinel(str):
    def __str__(self) -> str:
        return "MISSING"

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING: Any = MissingSentinel("MISSING")


@dataclasses.dataclass(eq=True)
class TimedFeature:
    enabled: bool = False
    time: int = 60

    def to_dict(self) -> dict:
        return {"enabled": self.enabled, "time": self.time}


def add_property(inst: object, name: str, method: Callable) -> None:
    cls = type(inst)
    if not hasattr(cls, "__perinstance"):
        cls = type(cls.__name__, (cls,), {})
        cls.__perinstance = True
        inst.__class__ = cls
    setattr(cls, name, property(method))


def get_time_string(seconds: int | float) -> str:
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    if d > 0:
        msg = "{0}d {1}h"
    elif d == 0 and h > 0:
        msg = "{1}h {2}m"
    elif d == 0 and h == 0 and m > 0:
        msg = "{2}m {3}s"
    elif d == 0 and h == 0 and m == 0 and s > 0:
        msg = "{3}s"
    else:
        msg = ""
    return msg.format(d, h, m, s)


def format_time(duration: int | float) -> str:
    """Formats the given time into DD:HH:MM:SS"""
    seconds = int(duration // 1000)
    days, seconds = divmod(seconds, 24 * 60 * 60)
    hours, seconds = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(seconds, 60)
    day = f"{days:02d}:" if days else ""
    hour = f"{hours:02d}:" if hours or day else ""
    minutes = f"{minutes:02d}:"
    sec = f"{seconds:02d}"
    return f"{day}{hour}{minutes}{sec}"


class PlayerQueue(asyncio.Queue[T]):
    """A queue, useful for coordinating producer and consumer coroutines.

    If maxsize is less than or equal to zero, the queue size is infinite. If it
    is an integer greater than 0, then "await put()" will block when the
    queue reaches maxsize, until an item is removed by get().

    Unlike the standard library Queue, you can reliably know this Queue's size
    with qsize(), since your single-threaded asyncio application won't be
    interrupted between calling qsize() and doing an operation on the Queue.
    """

    _queue: collections.deque[T]
    raw_b64s: list[str]

    def __init__(self, maxsize=0):
        self._maxsize = maxsize
        self._loop = events.get_event_loop()

        # Futures.
        self._getters = collections.deque()
        # Futures.
        self._putters = collections.deque()
        self._unfinished_tasks = 0
        self._finished = locks.Event()
        self._finished.set()
        self._init(maxsize)

    # These do not exist in asyncio.Queue
    @property
    def raw_queue(self):
        return self._queue.copy()

    @raw_queue.setter
    def raw_queue(self, value: collections.deque[T]):
        if not isinstance(value, collections.deque):
            raise TypeError("Queue value must be a collections.deque[Track]")
        if self._maxsize and len(value) > self._maxsize:
            raise ValueError(f"Queue value cannot be longer than maxsize: {self._maxsize}")
        self._queue = value

    def popindex(self, index: int) -> T:
        value = self._queue[index]
        del self._queue[index]
        return value

    async def remove(self, value: T, duplicates: bool = False) -> tuple[list[T], int]:
        """Removes the first occurrence of a value from the queue.

        If duplicates is True, all occurrences of the value are removed.
        Returns the number of occurrences removed.
        """
        count = 0
        removed = []
        try:
            i = self._queue.index(value)
            removed.append(self.popindex(i))
            count += 1
            if duplicates:
                with contextlib.suppress(ValueError):
                    while value in self:
                        i = self._queue.index(value)
                        removed.append(self.popindex(i))
                        count += 1
            return removed, count
        except ValueError as e:
            raise IndexError("Value not in queue") from e

    def clear(self):
        """Remove all items from the queue."""
        self._queue.clear()
        for i in self._getters:
            i.cancel()
        self._getters.clear()
        for i in self._putters:
            i.cancel()
        self._putters.clear()

    async def shuffle(self):
        """Shuffle the queue."""
        if self.empty():
            return
        await asyncio.to_thread(random.shuffle, self._queue)

    def index(self, value: T) -> int:
        """Return first index of value."""
        return self._queue.index(value)

    def __contains__(self, obj: T) -> bool:
        return obj in self._queue

    def __len__(self):
        return len(self._queue)

    def __index__(self):
        return len(self._queue)

    def __getitem__(self, key: int | slice) -> T | list[T]:
        return self.popindex(key) if isinstance(key, int) else NotImplemented

    def __length_hint__(self):
        return len(self._queue)

    # These three are overridable in subclasses.

    def _init(self, maxsize: int):
        self._queue = collections.deque(maxlen=maxsize or None)
        self.raw_b64s = []

    def _get(self, index: int = None) -> T:
        r = self.popindex(index) if index is not None else self._queue.popleft()
        if r.track:
            self.raw_b64s.remove(r.track)
        return r

    def _put(self, items: list[T], index: int = None):
        if index is not None:
            for i in items:
                if index < 0:
                    self._queue.append(i)
                    if i.track:
                        self.raw_b64s.append(i.track)
                else:
                    self._queue.insert(index, i)
                    if i.track:
                        self.raw_b64s.append(i.track)
                    index += 1
        else:
            self._queue.extend(items)
            self.raw_b64s.extend([i.track for i in items if i.track])

    # End of the overridable methods.

    @staticmethod
    def _wakeup_next(waiters):
        # Wake up the next waiter (if any) that isn't cancelled.
        while waiters:
            waiter = waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    def __repr__(self):
        return f"<{type(self).__name__} at {id(self):#x} {self._format()}>"

    def __str__(self):
        return f"<{type(self).__name__} {self._format()}>"

    __class_getitem__ = classmethod(GenericAlias)

    def _format(self):
        result = f"maxsize={self._maxsize!r}"
        if getattr(self, "_queue", None):
            result += f" _queue={list(self._queue)!r}"
        if self._getters:
            result += f" _getters[{len(self._getters)}]"
        if self._putters:
            result += f" _putters[{len(self._putters)}]"
        if self._unfinished_tasks:
            result += f" tasks={self._unfinished_tasks}"
        return result

    def qsize(self) -> int:
        """Number of items in the queue."""
        return len(self._queue)

    size = qsize

    @property
    def maxsize(self) -> int:
        """Number of items allowed in the queue."""
        return self._maxsize

    def empty(self) -> bool:
        """Return True if the queue is empty, False otherwise."""
        return not len(self._queue)

    def full(self) -> bool:
        """Return True if there are maxsize items in the queue.

        Note: if the Queue was initialized with maxsize=0 (the default),
        then full() is never True.
        """
        return False if self._maxsize <= 0 else self.qsize() >= self._maxsize

    async def put(self, items: list[T], index: int = None) -> None:
        """Put an item into the queue.

        Put an item into the queue. If the queue is full, wait until a free
        slot is available before adding item.
        """
        while self.full():
            putter = self._loop.create_future()
            self._putters.append(putter)
            try:
                await putter
            except BaseException:
                putter.cancel()  # Just in case putter is not done yet.
                try:
                    # Clean self._putters from canceled putters.
                    self._putters.remove(putter)
                except ValueError:
                    # The putter could be removed from self._putters by a
                    # previous get_nowait call.
                    pass
                if not self.full() and not putter.cancelled():
                    # We were woken up by get_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._putters)
                raise
        return self.put_nowait(items, index)

    def put_nowait(self, items: list[T], index: int = None) -> None:
        """Put an item into the queue without blocking.

        If no free slot is immediately available, raise QueueFull.
        """
        if self.full():
            raise QueueFull
        self._put(items, index=index)
        self._unfinished_tasks += 1
        self._finished.clear()
        self._wakeup_next(self._getters)

    async def get(self, index: int = None) -> T:
        """Remove and return an item from the queue.

        If queue is empty, wait until an item is available.
        """
        while self.empty():
            getter = self._loop.create_future()
            self._getters.append(getter)
            try:
                await getter
            except BaseException:
                getter.cancel()  # Just in case getter is not done yet.
                try:
                    # Clean self._getters from canceled getters.
                    self._getters.remove(getter)
                except ValueError:
                    # The getter could be removed from self._getters by a
                    # previous put_nowait call.
                    pass
                if not self.empty() and not getter.cancelled():
                    # We were woken up by put_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._getters)
                raise
        return self.get_nowait(index=index)

    def get_nowait(self, index: int = None) -> T:
        """Remove and return an item from the queue.

        Return an item if one is immediately available, else raise QueueEmpty.
        """
        if self.empty():
            return None
        item = self._get(index=index)
        self._wakeup_next(self._putters)
        return item

    def task_done(self):
        """Indicate that a formerly enqueued task is complete.

        Used by queue consumers. For each get() used to fetch a task,
        a subsequent call to task_done() tells the queue that the processing
        on the task is complete.

        If a join() is currently blocking, it will resume when all items have
        been processed (meaning that a task_done() call was received for every
        item that had been put() into the queue).

        Raises ValueError if called more times than there were items placed in
        the queue.
        """
        if self._unfinished_tasks <= 0:
            raise ValueError("task_done() called too many times")
        self._unfinished_tasks -= 1
        if self._unfinished_tasks == 0:
            self._finished.set()

    async def join(self):
        """Block until all items in the queue have been gotten and processed.

        The count of unfinished tasks goes up whenever an item is added to the
        queue. The count goes down whenever a consumer calls task_done() to
        indicate that the item was retrieved and all work on it is complete.
        When the count of unfinished tasks drops to zero, join() unblocks.
        """
        if self._unfinished_tasks > 0:
            await self._finished.wait()


class TrackHistoryQueue(PlayerQueue[T]):
    def __int__(self, maxsize: int = 0) -> None:
        super().__init__(maxsize=maxsize)

    def _init(self, maxsize: int):
        super()._init(maxsize)

    def _put(self, items: list[T], index: int = None):
        if len(items) + self.qsize() > self.maxsize:
            diff = len(items) + self.qsize() - self.maxsize
            for _ in range(diff):
                self._queue.pop()
                self.raw_b64s.pop()
        if index is not None:
            for i in items:
                if index < 0:
                    self._queue.append(i)
                    self.raw_b64s.append(i.track)
                else:
                    self._queue.insert(index, i)
                    self.raw_b64s.insert(index, i.track)
                    index += 1
        else:
            self._queue.extendleft(items)
            for i, t in enumerate(items):
                self.raw_b64s.insert(i, t.track)

    def _get(self, index: int = None) -> T:
        r = self.popindex(index) if index is not None else self._queue.popleft()
        self.raw_b64s.pop(index if index is not None else -1)
        return r

    def put_nowait(self, items: list[T], index: int = None):
        """Put an item into the queue without blocking.

        If no free slot is immediately available, raise QueueFull.
        """
        self._put(items, index=index)
        self._unfinished_tasks += 1
        self._finished.clear()
        self._wakeup_next(self._getters)

    def get_nowait(self, index: int = None) -> T | None:
        """Remove and return an item from the queue.

        Return an item if one is immediately available, else raise QueueEmpty.
        """
        if self.empty():
            return None
        item = self._get(index=index)
        self._wakeup_next(self._putters)
        return item


class SegmentCategory(Enum):
    """
    Segment category
    """

    Sponsor = "sponsor"
    Selfpromo = "selfpromo"
    Interaction = "interaction"
    Intro = "intro"
    Outro = "outro"
    Preview = "preview"
    MusicOfftopic = "music_offtopic"
    Filler = "filler"

    @classmethod
    def get_category(cls, segment_type: str) -> SegmentCategory:
        """
        Get segment category
        """
        if segment_type == "intro":
            return SegmentCategory.Intro
        elif segment_type == "outro":
            return SegmentCategory.Outro
        elif segment_type == "preview":
            return SegmentCategory.Preview
        elif segment_type == "music_offtopic":
            return SegmentCategory.MusicOfftopic
        elif segment_type == "filler":
            return SegmentCategory.Filler
        elif segment_type == "sponsor":
            return SegmentCategory.Sponsor
        elif segment_type == "selfpromo":
            return SegmentCategory.Selfpromo
        elif segment_type == "interaction":
            return SegmentCategory.Interaction
        else:
            raise ValueError(f"Unknown segment type: {segment_type}")

    @classmethod
    def get_category_name(cls, segment_type: str) -> str:
        """
        Get segment category name
        """
        return cls.get_category(segment_type).name

    @classmethod
    def get_category_from_name(cls, category_name: str) -> SegmentCategory:
        """
        Get segment category from name
        """
        return SegmentCategory[category_name]

    @classmethod
    def get_category_list(cls) -> list[SegmentCategory]:
        """
        Get segment category list
        """
        return list(cls)

    @classmethod
    def get_category_list_name(cls) -> list[str]:
        """
        Get segment category list name
        """
        return [category.name for category in cls]

    @classmethod
    def get_category_list_value(cls) -> list[str]:
        """
        Get segment category list value
        """
        return [category.value for category in cls]


class Segment:
    __slots__ = ("category", "start", "end")

    def __init__(self, /, category: str, start: float, end: float):
        self.category = category
        self.start = start
        self.end = end


class ExponentialBackoffWithReset(ExponentialBackoff):
    """
    Exponential backoff with reset
    """

    def __init__(self, base: int = 1, *, integral: T = False):
        super().__init__(base=base, integral=integral)

    def reset(self):
        """
        Reset
        """
        self._last_invocation: float = time.monotonic()
        self._exp = 0


class PyLavContext(_OriginalContextClass):
    _original_ctx_or_interaction: ContextT | InteractionT | None
    bot: BotT
    interaction: InteractionT | None

    def __init__(
        self,
        *,
        message: discord.Message,
        bot: BotT,
        view: StringView,
        args: list[Any] = D_MISSING,
        kwargs: dict[str, Any] = D_MISSING,
        prefix: str | None = None,
        command: Command[Any, ..., Any] | None = None,  # noqa
        invoked_with: str | None = None,
        invoked_parents: list[str] = D_MISSING,
        invoked_subcommand: Command[Any, ..., Any] | None = None,  # noqa
        subcommand_passed: str | None = None,
        command_failed: bool = False,
        current_parameter: discord.ext.commands.Parameter | None = None,
        current_argument: str | None = None,
        interaction: InteractionT | None = None,
    ):
        super().__init__(
            message=message,
            bot=bot,
            view=view,
            args=args,
            kwargs=kwargs,
            prefix=prefix,
            command=command,
            invoked_with=invoked_with,
            invoked_parents=invoked_parents,
            invoked_subcommand=invoked_subcommand,
            subcommand_passed=subcommand_passed,
            command_failed=command_failed,
            current_parameter=current_parameter,
            current_argument=current_argument,
            interaction=interaction,
        )

        self._original_ctx_or_interaction = None
        self.lavalink = bot.lavalink
        self.pylav = bot.lavalink

    @discord.utils.cached_property
    def author(self) -> discord.User | discord.Member:
        """Union[:class:`~discord.User`, :class:`.Member`]:
        Returns the author associated with this context's command. Shorthand for :attr:`.Message.author`
        """
        # When using client.get_context() on  a button interaction the "author" becomes the bot user
        #   This ensures the original author remains the author of the context
        if isinstance(self._original_ctx_or_interaction, discord.Interaction):
            return self._original_ctx_or_interaction.user
        elif isinstance(self._original_ctx_or_interaction, DpyContext):
            return self._original_ctx_or_interaction.author
        else:
            return self.message.author

    @property
    def cog(self) -> CogT | None:
        """Optional[:class:`.Cog`]: Returns the cog associated with this context's command. None if it does not
        exist."""

        return None if self.command is None else self.command.cog

    @discord.utils.cached_property
    def guild(self) -> discord.Guild | None:
        """Optional[:class:`.Guild`]: Returns the guild associated with this context's command. None if not
        available."""
        return getattr(self.author, "guild", None)

    @discord.utils.cached_property
    def channel(self) -> discord.abc.MessageableChannel:
        """Union[:class:`.abc.Messageable`]: Returns the channel associated with this context's command.
        Shorthand for :attr:`.Message.channel`.
        """
        if isinstance(self._original_ctx_or_interaction, (discord.Interaction, DpyContext)):
            return self._original_ctx_or_interaction.channel  # type: ignore
        else:
            return self.message.channel

    @property
    def player(self) -> Player | None:
        """
        Get player
        """
        return self.lavalink.get_player(self.guild)

    async def connect_player(self, channel: discord.channel.VocalGuildChannel = None, self_deaf: bool = True) -> Player:
        """
        Connect player
        """
        requester = self.author
        channel = channel or self.author.voice.channel
        return await self.lavalink.connect_player(requester=requester, channel=channel, self_deaf=self_deaf)

    @property
    def original_ctx_or_interaction(self) -> ContextT | InteractionT | None:
        """
        Get original ctx or interaction
        """
        return self._original_ctx_or_interaction

    async def construct_embed(
        self,
        *,
        embed: discord.Embed = None,
        colour: discord.Colour | int | None = None,
        color: discord.Colour | int | None = None,
        title: str = None,
        type: EmbedType = "rich",
        url: str = None,
        description: str = None,
        timestamp: datetime.datetime = None,
        author_name: str = None,
        author_url: str = None,
        thumbnail: str = None,
        footer: str = None,
        footer_url: str = None,
        messageable: discord.abc.Messageable | InteractionT = None,
    ) -> discord.Embed:
        """
        Construct embed
        """
        return await self.lavalink.construct_embed(
            embed=embed,
            colour=colour,
            color=color,
            title=title,
            type=type,
            url=url,
            description=description,
            timestamp=timestamp,
            author_name=author_name,
            author_url=author_url,
            thumbnail=thumbnail,
            footer=footer,
            footer_url=footer_url,
            messageable=messageable or self,
        )

    @classmethod
    async def from_interaction(cls, interaction: InteractionT, /) -> PyLavContext:
        #  When using this on a button interaction it raises an error as expected.
        #   This makes the `get_context` method work with buttons by storing the original context

        added_dummy = False
        if isinstance(interaction, discord.Interaction) and interaction.command is None:
            setattr(interaction, "_cs_command", dummy_command)
            added_dummy = True
        instance = await super().from_interaction(interaction)
        if added_dummy:
            instance.command = None
        instance._original_ctx_or_interaction = interaction
        return instance

    def dispatch_command(
        self, message: discord.Message, command: Command, prefix: str, author: discord.abc.User, *args: str
    ) -> None:
        """
        Dispatch command
        """
        command_str = f"{prefix}{command.qualified_name} {' '.join(args)}"

        msg = copy(message)
        msg.author = author
        msg.content = command_str
        self.bot.dispatch("message", msg)


async def _process_commands(self, message: discord.Message, /):
    """
    Same as base method, but dispatches an additional event for cogs
    which want to handle normal messages differently to command
    messages,  without the overhead of additional get_context calls
    per cog.
    """
    if not message.author.bot:
        ctx = await self.get_context(message, cls=PyLavContext)
        if ctx.invoked_with and isinstance(message.channel, discord.PartialMessageable):
            _RED_LOGGER.warning(
                "Discarded a command message (ID: %s) with PartialMessageable channel: %r",
                message.id,
                message.channel,
            )
        else:
            await self.invoke(ctx)
    else:
        ctx = None

    if ctx is None or ctx.valid is False:
        self.dispatch("message_without_command", message)


async def _get_context(self: BotT, message: discord.Message | InteractionT, /, *, cls=PyLavContext) -> PyLavContext:
    return await super(self.__class__, self).get_context(message, cls=cls)  # noqa


@dpy_command.command(name="__dummy_command", hidden=True, disabled=True)
async def dummy_command(self, context: PyLavContext):
    """Does nothing."""


# Everything under here is taken from
#   https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/core/utils/__init__.py
#   and is licensed under the GPLv3 license (https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/LICENSE

_T = TypeVar("_T")
_S = TypeVar("_S")

# https://github.com/PyCQA/pylint/issues/2717


# Benchmarked to be the fastest method.
def deduplicate_iterables(*iterables):
    """
    Returns a list of all unique items in ``iterables``, in the order they
    were first encountered.
    """
    # dict insertion order is guaranteed to be preserved in 3.6+
    return list(dict.fromkeys(chain.from_iterable(iterables)))


# https://github.com/PyCQA/pylint/issues/2717
class AsyncFilter(AsyncIterator[_T], Awaitable[list[_T]]):  # pylint: disable=duplicate-bases
    """Class returned by `async_filter`. See that function for details.

    We don't recommend instantiating this class directly.
    """

    def __init__(
        self,
        func: Callable[[_T], bool | Awaitable[bool]],
        iterable: AsyncIterable[_T] | Iterable[_T],
    ) -> None:
        self.__func: Callable[[_T], bool | Awaitable[bool]] = func
        self.__iterable: AsyncIterable[_T] | Iterable[_T] = iterable

        # We assign the generator strategy based on the arguments' types
        if isinstance(iterable, AsyncIterable):
            if asyncio.iscoroutinefunction(func):
                self.__generator_instance = self.__async_generator_async_pred()
            else:
                self.__generator_instance = self.__async_generator_sync_pred()
        elif asyncio.iscoroutinefunction(func):
            self.__generator_instance = self.__sync_generator_async_pred()
        else:
            raise TypeError("Must be either an async predicate, an async iterable, or both.")

    async def __sync_generator_async_pred(self) -> AsyncIterator[_T]:
        for item in self.__iterable:
            if await self.__func(item):
                yield item

    async def __async_generator_sync_pred(self) -> AsyncIterator[_T]:
        async for item in self.__iterable:
            if self.__func(item):
                yield item

    async def __async_generator_async_pred(self) -> AsyncIterator[_T]:
        async for item in self.__iterable:
            if await self.__func(item):
                yield item

    async def __flatten(self) -> list[_T]:
        return [item async for item in self]

    def __aiter__(self):
        return self

    def __await__(self):
        # Simply return the generator filled into a list
        return self.__flatten().__await__()

    def __anext__(self) -> Awaitable[_T]:
        # This will use the generator strategy set in __init__
        return self.__generator_instance.__anext__()


def async_filter(
    func: Callable[[_T], bool | Awaitable[bool]],
    iterable: AsyncIterable[_T] | Iterable[_T],
) -> AsyncFilter[_T]:
    """Filter an (optionally async) iterable with an (optionally async) predicate.

    At least one of the arguments must be async.

    Parameters
    ----------
    func : Callable[[T], Union[bool, Awaitable[bool]]]
        A function or coroutine function which takes one item of ``iterable``
        as an argument, and returns ``True`` or ``False``.
    iterable : Union[AsyncIterable[_T], Iterable[_T]]
        An iterable or async iterable which is to be filtered.

    Raises
    ------
    TypeError
        If neither of the arguments are async.

    Returns
    -------
    AsyncFilter[T]
        An object which can either be awaited to yield a list of the filtered
        items, or can also act as an async iterator to yield items one by one.

    """
    return AsyncFilter(func, iterable)


async def async_enumerate(async_iterable: AsyncIterable[_T], start: int = 0) -> AsyncIterator[tuple[int, _T]]:
    """Async iterable version of `enumerate`.

    Parameters
    ----------
    async_iterable : AsyncIterable[T]
        The iterable to enumerate.
    start : int
        The index to start from. Defaults to 0.

    Returns
    -------
    AsyncIterator[Tuple[int, T]]
        An async iterator of tuples in the form of ``(index, item)``.

    """
    async for item in async_iterable:
        yield start, item
        start += 1


async def _sem_wrapper(sem, task):
    async with sem:
        return await task


def bounded_gather_iter(
    *coros_or_futures, limit: int = 4, semaphore: asyncio.Semaphore | None = None
) -> Iterator[Awaitable[Any]]:
    """
    An iterator that returns tasks as they are ready, but limits the
    number of tasks running at a time.

    Parameters
    ----------
    *coros_or_futures
        The awaitables to run in a bounded concurrent fashion.
    limit : Optional[`int`]
        The maximum number of concurrent tasks. Used when no ``semaphore``
        is passed.
    semaphore : Optional[:class:`asyncio.Semaphore`]
        The semaphore to use for bounding tasks. If `None`, create one
        using ``loop`` and ``limit``.

    Raises
    ------
    TypeError
        When invalid parameters are passed
    """
    loop = asyncio.get_running_loop()

    if semaphore is None:
        if not isinstance(limit, int) or limit <= 0:
            raise TypeError("limit must be an int > 0")

        semaphore = asyncio.Semaphore(limit)

    pending = []

    for cof in coros_or_futures:
        if asyncio.isfuture(cof) and cof._loop is not loop:
            raise ValueError("futures are tied to different event loops")

        cof = _sem_wrapper(semaphore, cof)
        pending.append(cof)

    return asyncio.as_completed(pending)


def bounded_gather(
    *coros_or_futures,
    return_exceptions: bool = False,
    limit: int = 4,
    semaphore: asyncio.Semaphore | None = None,
) -> Awaitable[list[Any]]:
    """
    A semaphore-bounded wrapper to :meth:`asyncio.gather`.

    Parameters
    ----------
    *coros_or_futures
        The awaitables to run in a bounded concurrent fashion.
    return_exceptions : bool
        If true, gather exceptions in the result list instead of raising.
    limit : Optional[`int`]
        The maximum number of concurrent tasks. Used when no ``semaphore``
        is passed.
    semaphore : Optional[:class:`asyncio.Semaphore`]
        The semaphore to use for bounding tasks. If `None`, create one
        using ``loop`` and ``limit``.

    Raises
    ------
    TypeError
        When invalid parameters are passed
    """
    asyncio.get_running_loop()

    if semaphore is None:
        if not isinstance(limit, int) or limit <= 0:
            raise TypeError("limit must be an int > 0")

        semaphore = asyncio.Semaphore(limit)

    tasks = (_sem_wrapper(semaphore, task) for task in coros_or_futures)

    return asyncio.gather(*tasks, return_exceptions=return_exceptions)


class AsyncIter(AsyncIterator[_T], Awaitable[list[_T]]):  # pylint: disable=duplicate-bases
    """Asynchronous iterator yielding items from ``iterable``
    that sleeps for ``delay`` seconds every ``steps`` items.

    Parameters
    ----------
    iterable: Iterable
        The iterable to make async.
    delay: Union[float, int]
        The amount of time in seconds to sleep.
    steps: int
        The number of iterations between sleeps.

    Raises
    ------
    ValueError
        When ``steps`` is lower than 1.

    Examples
    --------
    >>> from pylav.utils import AsyncIter
    >>> async for value in AsyncIter(range(3)):
    ...     print(value)
    0
    1
    2

    """

    def __init__(self, iterable: Iterable[_T], delay: float | int = 0, steps: int = 100) -> None:
        if steps < 1:
            raise ValueError("Steps must be higher than or equals to 1")
        self._delay = delay
        self._iterator = iter(iterable)
        self._i = 0
        self._steps = steps
        self._map = None

    def __aiter__(self) -> AsyncIter[_T]:
        return self

    async def __anext__(self) -> _T:
        try:
            item = next(self._iterator)
        except StopIteration as e:
            raise StopAsyncIteration from e
        if self._i == self._steps:
            self._i = 0
            await asyncio.sleep(self._delay)
        self._i += 1
        return await maybe_coroutine(self._map, item) if self._map is not None else item

    def __await__(self) -> Generator[Any, None, list[_T]]:
        """Returns a list of the iterable.

        Examples
        --------
        >>> from pylav.utils import AsyncIter
        >>> iterator = AsyncIter(range(5))
        >>> await iterator
        [0, 1, 2, 3, 4]

        """
        return self.flatten().__await__()

    async def next(self, default: Any = ...) -> _T:
        """Returns a next entry of the iterable.

        Parameters
        ----------
        default: Optional[Any]
            The value to return if the iterator is exhausted.

        Raises
        ------
        StopAsyncIteration
            When ``default`` is not specified and the iterator has been exhausted.

        Examples
        --------
        >>> from pylav.utils import AsyncIter
        >>> iterator = AsyncIter(range(5))
        >>> await iterator.next()
        0
        >>> await iterator.next()
        1

        """
        try:
            value = await self.__anext__()
        except StopAsyncIteration:
            if default is ...:
                raise
            value = default
        return value

    async def flatten(self) -> list[_T]:
        """Returns a list of the iterable.

        Examples
        --------
        >>> from pylav.utils import AsyncIter
        >>> iterator = AsyncIter(range(5))
        >>> await iterator.flatten()
        [0, 1, 2, 3, 4]

        """
        return [item async for item in self]

    def filter(self, function: Callable[[_T], bool | Awaitable[bool]]) -> AsyncFilter[_T]:
        """Filter the iterable with an (optionally async) predicate.

        Parameters
        ----------
        function: Callable[[T], Union[bool, Awaitable[bool]]]
            A function or coroutine function which takes one item of ``iterable``
            as an argument, and returns ``True`` or ``False``.

        Returns
        -------
        AsyncFilter[T]
            An object which can either be awaited to yield a list of the filtered
            items, or can also act as an async iterator to yield items one by one.

        Examples
        --------
        >>> from pylav.utils import AsyncIter
        >>> def predicate(value):
        ...     return value <= 5
        >>> iterator = AsyncIter([1, 10, 5, 100])
        >>> async for i in iterator.filter(predicate):
        ...     print(i)
        1
        5

        >>> from pylav.utils import AsyncIter
        >>> def predicate(value):
        ...     return value <= 5
        >>> iterator = AsyncIter([1, 10, 5, 100])
        >>> await iterator.filter(predicate)
        [1, 5]

        """
        return async_filter(function, self)

    def enumerate(self, start: int = 0) -> AsyncIterator[tuple[int, _T]]:
        """Async iterable version of `enumerate`.

        Parameters
        ----------
        start: int
            The index to start from. Defaults to 0.

        Returns
        -------
        AsyncIterator[Tuple[int, T]]
            An async iterator of tuples in the form of ``(index, item)``.

        Examples
        --------
        >>> from pylav.utils import AsyncIter
        >>> iterator = AsyncIter(['one', 'two', 'three'])
        >>> async for i in iterator.enumerate(start=10):
        ...     print(i)
        (10, 'one')
        (11, 'two')
        (12, 'three')

        """
        return async_enumerate(self, start)

    async def without_duplicates(self) -> AsyncIterator[_T]:
        """
        Iterates while omitting duplicated entries.

        Examples
        --------
        >>> from pylav.utils import AsyncIter
        >>> iterator = AsyncIter([1,2,3,3,4,4,5])
        >>> async for i in iterator.without_duplicates():
        ...     print(i)
        1
        2
        3
        4
        5

        """
        _temp = set()
        async for item in self:
            if item not in _temp:
                yield item
                _temp.add(item)
        del _temp

    async def find(
        self,
        predicate: Callable[[_T], bool | Awaitable[bool]],
        default: Any | None = None,
    ) -> AsyncIterator[_T]:
        """Calls ``predicate`` over items in iterable and return first value to match.

        Parameters
        ----------
        predicate: Union[Callable, Coroutine]
            A function that returns a boolean-like result. The predicate provided can be a coroutine.
        default: Optional[Any]
            The value to return if there are no matches.

        Raises
        ------
        TypeError
            When ``predicate`` is not a callable.

        Examples
        --------
        >>> from pylav.utils import AsyncIter
        >>> await AsyncIter(range(3)).find(lambda x: x == 1)
        1
        """
        while True:
            try:
                elem = await self.__anext__()
            except StopAsyncIteration:
                return default
            ret = await maybe_coroutine(predicate, elem)
            if ret:
                return elem

    def map(self, func: Callable[[_T], _S | Awaitable[_S]]) -> AsyncIter[_S]:
        """Set the mapping callable for this instance of `AsyncIter`.

        .. important::
            This should be called after AsyncIter initialization and before any other of its methods.

        Parameters
        ----------
        func: Union[Callable, Coroutine]
            The function to map values to. The function provided can be a coroutine.

        Raises
        ------
        TypeError
            When ``func`` is not a callable.

        Examples
        --------
        >>> from pylav.utils import AsyncIter
        >>> async for value in AsyncIter(range(3)).map(bool):
        ...     print(value)
        False
        True
        True

        """

        if not callable(func):
            raise TypeError("Mapping must be a callable.")
        self._map = func
        return self
