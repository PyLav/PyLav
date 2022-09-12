from __future__ import annotations

import asyncio
import collections
import contextlib
import dataclasses
import datetime
import functools
import math
import os
import pathlib
import platform
import random
import re
import shutil
import sys
import threading
import time
from asyncio import QueueFull, events, locks
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Generator, Iterable, Iterator, Sequence
from copy import copy
from enum import Enum
from functools import _make_key  # type: ignore
from itertools import chain
from re import Pattern
from types import GenericAlias
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast

import discord  # type: ignore
import psutil
from discord.backoff import ExponentialBackoff
from discord.ext import commands
from discord.ext import commands as dpy_command
from discord.ext.commands.view import StringView
from discord.types.embed import EmbedType
from discord.utils import MISSING as D_MISSING  # noqa
from discord.utils import maybe_coroutine


@contextlib.contextmanager
def add_env_path(path: str | os.PathLike) -> Iterator[str]:
    path = os.fspath(path)
    existing_path = "PATH" in os.environ
    old_path = os.environ["PATH"] if existing_path else None
    try:
        if path not in os.environ["PATH"]:
            yield path + os.pathsep + os.environ["PATH"]
        else:
            yield os.environ["PATH"]
    finally:
        if existing_path:
            os.environ["PATH"] = old_path
        else:
            del os.environ["PATH"]


def get_true_path(executable: str, fallback: T = None) -> str | T | None:
    path = os.environ.get("JAVA_HOME", executable)
    with add_env_path(path if os.path.isdir(path) else os.path.split(path)[0]) as path_string:
        executable = shutil.which(executable, path=path_string)
    return executable or fallback


from pylav.envvars import JAVA_EXECUTABLE  # isort:skip
from pylav.types import BotT, CogT, ContextT, InteractionT  # isort:skip

try:
    from redbot.core.commands import Command
    from redbot.core.commands import Context as _OriginalContextClass
except ImportError:
    from discord.ext.commands import Command
    from discord.ext.commands import Context as _OriginalContextClass

from discord.ext.commands import Context as DpyContext  # isort:skip

if TYPE_CHECKING:
    from pylav.node import Node
    from pylav.player import Player

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
    "shorten_string",
)

from pylav._logging import getLogger

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLavPlayer", pathlib.Path(__file__))
except ImportError:
    _ = lambda x: x

T = TypeVar("T")

LOGGER = getLogger("PyLav.utils")
_RED_LOGGER = getLogger("red")

_LOCK = threading.Lock()


def get_max_allocation_size(executable: str) -> tuple[int, bool]:
    if platform.architecture(executable)[0] == "64bit":
        max_heap_allowed = psutil.virtual_memory().total
        thinks_is_64_bit = True
    else:
        max_heap_allowed = 4 * 1024**3
        thinks_is_64_bit = False
    return max_heap_allowed, thinks_is_64_bit


def _calculate_ram(max_allocation: int, is_64bit: bool) -> tuple[str, str, int, int]:
    min_ram_int = 64 * 1024**2
    max_ram_allowed = max_allocation * 0.5 if is_64bit else max_allocation
    max_ram_int = max(min_ram_int, max_ram_allowed)
    size_name = ("", "K", "M", "G", "T")
    i = int(math.floor(math.log(min_ram_int, 1024)))
    p = math.pow(1024, i)
    s = int(min_ram_int // p)
    min_ram = f"{s}{size_name[i]}"

    i = int(math.floor(math.log(max_ram_int, 1024)))
    p = math.pow(1024, i)
    s = int(max_ram_int // p)
    max_ram = f"{s}{size_name[i]}"

    return min_ram, max_ram, min_ram_int, max_ram_int


def get_jar_ram_defaults() -> tuple[str, str, int, int]:
    # We don't know the java executable at this stage - not worth the extra work required here
    max_allocation, is_64bit = get_max_allocation_size(sys.executable)
    min_ram, max_ram, min_ram_int, max_ram_int = _calculate_ram(max_allocation, is_64bit)
    return min_ram, max_ram, min_ram_int, max_ram_int


def get_jar_ram_actual(executable: str) -> tuple[str, str, int, int]:
    if not executable:
        executable = JAVA_EXECUTABLE
    executable = get_true_path(executable, sys.executable)
    max_allocation, is_64bit = get_max_allocation_size(executable)
    min_ram, max_ram, min_ram_int, max_ram_int = _calculate_ram(max_allocation, is_64bit)
    return min_ram, max_ram, min_ram_int, max_ram_int


def shorten_string(string: str, max_length: int, right: bool = True) -> str:
    if len(string) > max_length:
        if right:
            return string[: max_length - 1] + "\N{HORIZONTAL ELLIPSIS}"
        else:
            return string[(max_length - 1) * -1 :] + "\N{HORIZONTAL ELLIPSIS}"
    return string


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

    def __call__(cls, *args, **kwargs):
        # sourcery skip: instance-method-first-arg-name
        if cls not in cls._instances:
            cls._locked_call(*args, **kwargs)
        return cls._instances[cls]

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

    def __int__(self):
        return 0

    def __float__(self):
        return 0.0

    def __len__(self):
        return 0

    def __iter__(self):
        return iter([])

    def __getitem__(self, item):
        return None

    def __getattr__(self, item):
        return None

    def __divmod__(self, other):
        return (0, 0)

    def __rdivmod__(self, other):
        return (0, 0)

    def __floor__(self):
        return 0

    def __ceil__(self):
        return 0

    def __round__(self):
        return 0

    def __trunc__(self):
        return 0

    def __add__(self, other):
        return other

    def __radd__(self, other):
        return other

    def __sub__(self, other):
        return other

    def __rsub__(self, other):
        return other

    def __mul__(self, other):
        return 0

    def __rmul__(self, other):
        return 0

    def __matmul__(self, other):
        return 0

    def __rmatmul__(self, other):
        return 0

    def __mod__(self, other):
        return 0

    def __rmod__(self, other):
        return 0

    def __div__(self, other):
        return 0

    def __rdiv__(self, other):
        return 0

    def __truediv__(self, other):
        return 0

    def __rtruediv__(self, other):
        return 0

    def __floordiv__(self, other):
        return 0

    def __rfloordiv__(self, other):
        return 0

    def __pow__(self, other):
        return 0

    def __rpow__(self, other):
        return 0

    def __lshift__(self, other):
        return 0

    def __rlshift__(self, other):
        return 0


MISSING: Any = MissingSentinel("MISSING")


@dataclasses.dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class TimedFeature:
    enabled: bool = False
    time: int = 60

    def to_dict(self) -> dict:
        return {"enabled": self.enabled, "time": self.time}

    @classmethod
    def from_dict(cls, d: dict) -> TimedFeature:
        return cls(enabled=d["enabled"], time=d["time"])

    from_json = from_dict


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

    hour = _("hour")
    minute = _("minute")
    second = _("second")
    day = _("day")
    days = _("days")
    hours = _("hours")
    minutes = _("minutes")
    seconds = _("seconds")

    if d > 0:
        return f"{d} {day if d == 1 else days} {h} {hour if h == 1 else hours}"

    elif d == 0 and h > 0:
        return f"{h} {hour if h == 1 else hours} {m} {minute if m == 1 else minutes}"

    elif d == 0 and h == 0 and m > 0:
        return f"{m} {minute if m == 1 else minutes} {s} {second if s == 1 else seconds}"

    elif d == 0 and h == 0 and m == 0 and s >= 0:
        return f"{s} {second if s == 1 else seconds}"
    else:
        return ""


def format_time(duration: int | float) -> str:
    """Formats the given time into DD:HH:MM:SS"""
    seconds = int(duration // 1000)
    if seconds == 0:
        return _("Unknown")
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

    __slots__ = ("_queue", "_maxsize", "_getters", "_putters", "_unfinished_tasks", "_finished", "_loop")

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
        """Remove all items from the queue"""
        self._queue.clear()
        for i in self._getters:
            i.cancel()
        self._getters.clear()
        for i in self._putters:
            i.cancel()
        self._putters.clear()

    async def shuffle(self):
        """Shuffle the queue"""
        if self.empty():
            return
        await asyncio.to_thread(random.shuffle, self._queue)

    def index(self, value: T) -> int:
        """Return first index of value"""
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
        """Number of items in the queue"""
        return len(self._queue)

    size = qsize

    @property
    def maxsize(self) -> int:
        """Number of items allowed in the queue"""
        return self._maxsize

    def empty(self) -> bool:
        """Return True if the queue is empty, False otherwise"""
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
                with contextlib.suppress(ValueError):
                    # Clean self._putters from canceled putters.
                    self._putters.remove(putter)
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
                getter.cancel()
                with contextlib.suppress(ValueError):
                    self._getters.remove(getter)
                if not self.empty() and not getter.cancelled():
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
    __slots__ = ("_queue", "_maxsize", "_getters", "_putters", "_unfinished_tasks", "_finished", "_loop")

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
        return [category.value for category in cls]  # type: ignore


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
    client: BotT
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
        exist"""

        return None if self.command is None else self.command.cog

    @discord.utils.cached_property
    def guild(self) -> discord.Guild | None:
        """Optional[:class:`.Guild`]: Returns the guild associated with this context's command. None if not
        available"""
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
        self, message: discord.Message, command: Command, author: discord.abc.User, args: list[str], prefix: str = None
    ) -> None:
        """
        Dispatch command
        """
        command_str = f"{prefix}{command.qualified_name} {' '.join(args)}"
        msg = copy(message)
        msg.author = author
        msg.content = command_str
        self.bot.dispatch("message", msg)

    async def send_interactive(
        self, messages: Iterable[str], box_lang: str = None, timeout: int = 15, embed: bool = False
    ) -> list[discord.Message]:
        """Send multiple messages interactively.

        The user will be prompted for whether or not they would like to view
        the next message, one at a time. They will also be notified of how
        many messages are remaining on each prompt.

        Parameters
        ----------
        messages : `iterable` of `str`
            The messages to send.
        box_lang : str
            If specified, each message will be contained within a codeblock of
            this language.
        timeout : int
            How long the user has to respond to the prompt before it times out.
            After timing out, the bot deletes its prompt message.
        embed : bool
            Whether or not to send the messages as embeds.

        """
        messages = tuple(messages)
        ret = []

        for idx, page in enumerate(messages, 1):
            if box_lang is None:
                msg = (
                    await self.send(embed=await self.lavalink.construct_embed(description=page, messageable=self))
                    if embed
                    else await self.send(page)
                )
            elif embed:
                msg = await self.send(
                    embed=await self.lavalink.construct_embed(
                        description=f"```{box_lang}\n{page}\n```", messageable=self
                    )
                )
            else:
                msg = await self.send(f"```{box_lang}\n{page}\n```")
            ret.append(msg)
            n_remaining = len(messages) - idx
            if n_remaining > 0:
                query = await self.send(
                    _("{} remaining. Type `more` to continue.").format(
                        _("There is still 1 message")
                        if n_remaining == 1
                        else _("There are still {remaning} messages").format(remaning=n_remaining)
                    )
                )
                try:
                    resp = await self.bot.wait_for(
                        "message",
                        check=MessagePredicate.lower_equal_to("more", self),
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    with contextlib.suppress(discord.HTTPException):
                        await query.delete()
                    break
                else:
                    try:
                        await self.channel.delete_messages((query, resp))
                    except (discord.HTTPException, AttributeError):
                        # In case the bot can't delete other users' messages,
                        # or is not a bot account
                        # or channel is a DM
                        with contextlib.suppress(discord.HTTPException):
                            await query.delete()
        return ret


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
    """Does nothing"""


async def sort_key_nodes(node: Node, region: str = None) -> float:
    return await node.penalty_with_region(region)


# Everything under here is taken from
#   https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/core/utils/__init__.py
#   and is licensed under the GPLv3 license (https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/LICENSE

_T = TypeVar("_T")
_S = TypeVar("_S")

# https://github.com/PyCQA/pylint/issues/2717

_ID_RE = re.compile(r"([0-9]{15,20})$")
_USER_MENTION_RE = re.compile(r"<@!?([0-9]{15,20})>$")
_CHAN_MENTION_RE = re.compile(r"<#([0-9]{15,20})>$")
_ROLE_MENTION_RE = re.compile(r"<@&([0-9]{15,20})>$")


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

    __slots__ = ("__func", "__iterable", "__generator_instance")

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
            raise TypeError("Must be either an async predicate, an async iterable, or both")

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

    __slots__ = ("_delay", "_iterator", "_i", "_steps", "_map")

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
            raise TypeError("Mapping must be a callable")
        self._map = func
        return self


class MessagePredicate(Callable[[discord.Message], bool]):
    """A simple collection of predicates for message events.

    These predicates intend to help simplify checks in message events
    and reduce boilerplate code.

    This class should be created through the provided classmethods.
    Instances of this class are callable message predicates, i.e. they
    return ``True`` if a message matches the criteria.

    All predicates are combined with :meth:`MessagePredicate.same_context`.

    Examples
    --------
    Waiting for a response in the same channel and from the same
    author::

        await bot.wait_for("message", check=MessagePredicate.same_context(ctx))

    Waiting for a response to a yes or no question::

        pred = MessagePredicate.yes_or_no(ctx)
        await bot.wait_for("message", check=pred)
        if pred.result is True:
            # User responded "yes"
            ...

    Getting a member object from a user's response::

        pred = MessagePredicate.valid_member(ctx)
        await bot.wait_for("message", check=pred)
        member = pred.result

    Attributes
    ----------
    result : Any
        The object which the message content matched with. This is
        dependent on the predicate used - see each predicate's
        documentation for details, not every method will assign this
        attribute. Defaults to ``None``.

    """

    __slots__ = ("result", "_pred")

    def __init__(self, predicate: Callable[[MessagePredicate, discord.Message], bool]) -> None:
        self._pred: Callable[[MessagePredicate, discord.Message], bool] = predicate
        self.result = None

    def __call__(self, message: discord.Message) -> bool:
        return self._pred(self, message)

    @classmethod
    def same_context(
        cls,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the message fits the described context.

        Parameters
        ----------
        ctx : Optional[Context]
            The current invocation context.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            The channel we expect a message in. If unspecified,
            defaults to ``ctx.channel``. If ``ctx`` is unspecified
            too, the message's channel will be ignored.
        user : Optional[discord.abc.User]
            The user we expect a message from. If unspecified,
            defaults to ``ctx.author``. If ``ctx`` is unspecified
            too, the message's author will be ignored.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        if ctx is not None:
            channel = channel or ctx.channel
            user = user or ctx.author

        return cls(
            lambda self, m: (user is None or user.id == m.author.id) and (channel is None or channel.id == m.channel.id)
        )

    @classmethod
    def cancelled(
        cls,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the message is ``[p]cancel``.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        return cls(lambda self, m: (same_context(m) and m.content.lower() == f"{ctx.prefix}cancel"))

    @classmethod
    def yes_or_no(
        cls,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the message is "yes"/"y" or "no"/"n".

        This will assign ``True`` for *yes*, or ``False`` for *no* to
        the `result` attribute.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            content = m.content.lower()
            if content in ("yes", "y"):
                self.result = True
            elif content in ("no", "n"):
                self.result = False
            else:
                return False
            return True

        return cls(predicate)

    @classmethod
    def valid_int(
        cls,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response is an integer.

        Assigns the response to `result` as an `int`.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            try:
                self.result = int(m.content)
            except ValueError:
                return False
            else:
                return True

        return cls(predicate)

    @classmethod
    def valid_float(
        cls,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response is a float.

        Assigns the response to `result` as a `float`.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            try:
                self.result = float(m.content)
            except ValueError:
                return False
            else:
                return True

        return cls(predicate)

    @classmethod
    def positive(
        cls,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response is a positive number.

        Assigns the response to `result` as a `float`.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            try:
                number = float(m.content)
            except ValueError:
                return False
            else:
                if number > 0:
                    self.result = number
                    return True
                else:
                    return False

        return cls(predicate)

    @classmethod
    def valid_role(
        cls,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response refers to a role in the current guild.

        Assigns the matching `discord.Role` object to `result`.

        This predicate cannot be used in DM.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        guild = cls._get_guild(ctx, channel, cast(discord.Member, user))

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False

            role = self._find_role(guild, m.content)
            if role is None:
                return False

            self.result = role
            return True

        return cls(predicate)

    @classmethod
    def valid_member(
        cls,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response refers to a member in the current guild.

        Assigns the matching `discord.Member` object to `result`.

        This predicate cannot be used in DM.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        guild = cls._get_guild(ctx, channel, cast(discord.Member, user))

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False

            match = _ID_RE.match(m.content) or _USER_MENTION_RE.match(m.content)
            if match:
                result = guild.get_member(int(match.group(1)))
            else:
                result = guild.get_member_named(m.content)

            if result is None:
                return False
            self.result = result
            return True

        return cls(predicate)

    @classmethod
    def valid_text_channel(
        cls,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response refers to a text channel in the current guild.

        Assigns the matching `discord.TextChannel` object to `result`.

        This predicate cannot be used in DM.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        guild = cls._get_guild(ctx, channel, cast(discord.Member, user))

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False

            match = _ID_RE.match(m.content) or _CHAN_MENTION_RE.match(m.content)
            if match:
                result = guild.get_channel(int(match.group(1)))
            else:
                result = discord.utils.get(guild.text_channels, name=m.content)

            if not isinstance(result, discord.TextChannel):
                return False
            self.result = result
            return True

        return cls(predicate)

    @classmethod
    def has_role(
        cls,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response refers to a role which the author has.

        Assigns the matching `discord.Role` object to `result`.

        One of ``user`` or ``ctx`` must be supplied. This predicate
        cannot be used in DM.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        guild = cls._get_guild(ctx, channel, cast(discord.Member, user))
        if user is None:
            if ctx is None:
                raise TypeError("One of `user` or `ctx` must be supplied to `MessagePredicate.has_role`.")
            user = ctx.author

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False

            role = self._find_role(guild, m.content)
            if role is None or role not in user.roles:
                return False

            self.result = role
            return True

        return cls(predicate)

    @classmethod
    def equal_to(
        cls,
        value: str,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response is equal to the specified value.

        Parameters
        ----------
        value : str
            The value to compare the response with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        return cls(lambda self, m: same_context(m) and m.content == value)

    @classmethod
    def lower_equal_to(
        cls,
        value: str,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response *as lowercase* is equal to the specified value.

        Parameters
        ----------
        value : str
            The value to compare the response with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        return cls(lambda self, m: same_context(m) and m.content.lower() == value)

    @classmethod
    def less(
        cls,
        value: int | float,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response is less than the specified value.

        Parameters
        ----------
        value : Union[int, float]
            The value to compare the response with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        valid_int = cls.valid_int(ctx, channel, user)
        valid_float = cls.valid_float(ctx, channel, user)
        return cls(lambda self, m: (valid_int(m) or valid_float(m)) and float(m.content) < value)

    @classmethod
    def greater(
        cls,
        value: int | float,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response is greater than the specified value.

        Parameters
        ----------
        value : Union[int, float]
            The value to compare the response with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        valid_int = cls.valid_int(ctx, channel, user)
        valid_float = cls.valid_float(ctx, channel, user)
        return cls(lambda self, m: (valid_int(m) or valid_float(m)) and float(m.content) > value)

    @classmethod
    def length_less(
        cls,
        length: int,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response's length is less than the specified length.

        Parameters
        ----------
        length : int
            The value to compare the response's length with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        return cls(lambda self, m: same_context(m) and len(m.content) <= length)

    @classmethod
    def length_greater(
        cls,
        length: int,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response's length is greater than the specified length.

        Parameters
        ----------
        length : int
            The value to compare the response's length with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        return cls(lambda self, m: same_context(m) and len(m.content) >= length)

    @classmethod
    def contained_in(
        cls,
        collection: Sequence[str],
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response is contained in the specified collection.

        The index of the response in the ``collection`` sequence is
        assigned to the `result` attribute.

        Parameters
        ----------
        collection : Sequence[str]
            The collection containing valid responses.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            try:
                self.result = collection.index(m.content)
            except ValueError:
                return False
            else:
                return True

        return cls(predicate)

    @classmethod
    def lower_contained_in(
        cls,
        collection: Sequence[str],
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Same as :meth:`contained_in`, but the response is set to lowercase before matching.

        Parameters
        ----------
        collection : Sequence[str]
            The collection containing valid lowercase responses.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            try:
                self.result = collection.index(m.content.lower())
            except ValueError:
                return False
            else:
                return True

        return cls(predicate)

    @classmethod
    def regex(
        cls,
        pattern: Pattern[str] | str,
        ctx: commands.Context | None = None,
        channel: discord.TextChannel | discord.Thread | discord.DMChannel | None = None,
        user: discord.abc.User | None = None,
    ) -> MessagePredicate:
        """Match if the response matches the specified regex pattern.

        This predicate will use `re.search` to find a match. The
        resulting `match object <match-objects>` will be assigned
        to `result`.

        Parameters
        ----------
        pattern : Union[`pattern object <re-objects>`, str]
            The pattern to search for in the response.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.Thread`, `discord.DMChannel`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            pattern_obj = re.compile(pattern) if isinstance(pattern, str) else pattern
            match = pattern_obj.search(m.content)
            if match:
                self.result = match
                return True
            return False

        return cls(predicate)

    @staticmethod
    def _find_role(guild: discord.Guild, argument: str) -> discord.Role | None:
        return (
            guild.get_role(int(match.group(1)))
            if (match := _ID_RE.match(argument) or _ROLE_MENTION_RE.match(argument))
            else discord.utils.get(guild.roles, name=argument)
        )

    @staticmethod
    def _get_guild(
        ctx: commands.Context | None,
        channel: discord.TextChannel | discord.Thread | None,
        user: discord.Member | None,
    ) -> discord.Guild:
        if ctx is not None:
            return ctx.guild
        elif channel is not None:
            return channel.guild
        elif user is not None:
            return user.guild
