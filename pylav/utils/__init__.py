from __future__ import annotations

import asyncio
import collections
import contextlib
import random
import warnings
from asyncio import QueueFull, events, locks
from itertools import chain
from types import GenericAlias
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Generator,
    Iterable,
    Iterator,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from discord.utils import maybe_coroutine

__all__ = ("MISSING", "AsyncIter", "add_property", "format_time", "get_time_string", "Queue", "LifoQueue")

from red_commons.logging import getLogger

T = TypeVar("T")

LOGGER = getLogger("red.PyLink.utils")


class MissingSentinel(str):
    def __str__(self) -> str:
        return "MISSING"

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING: Any = MissingSentinel("MISSING")

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
    >>> from redbot.core.utils import AsyncIter
    >>> async for value in AsyncIter(range(3)):
    ...     print(value)
    0
    1
    2

    """

    def __init__(self, iterable: Iterable[_T], delay: float | int = 0, steps: int = 1) -> None:
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
        except StopIteration:
            raise StopAsyncIteration
        if self._i == self._steps:
            self._i = 0
            await asyncio.sleep(self._delay)
        self._i += 1
        return await maybe_coroutine(self._map, item) if self._map is not None else item

    def __await__(self) -> Generator[Any, None, list[_T]]:
        """Returns a list of the iterable.

        Examples
        --------
        >>> from redbot.core.utils import AsyncIter
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
        >>> from redbot.core.utils import AsyncIter
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
        >>> from redbot.core.utils import AsyncIter
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
        >>> from redbot.core.utils import AsyncIter
        >>> def predicate(value):
        ...     return value <= 5
        >>> iterator = AsyncIter([1, 10, 5, 100])
        >>> async for i in iterator.filter(predicate):
        ...     print(i)
        1
        5

        >>> from redbot.core.utils import AsyncIter
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
        >>> from redbot.core.utils import AsyncIter
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
        >>> from redbot.core.utils import AsyncIter
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
        >>> from redbot.core.utils import AsyncIter
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
        >>> from redbot.core.utils import AsyncIter
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


def format_time(time: int | float) -> str:
    """Formats the given time into DD:HH:MM:SS"""
    seconds = int(time // 1000)
    days, seconds = divmod(seconds, 24 * 60 * 60)
    hours, seconds = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(seconds, 60)
    day = ""
    hour = ""
    if days:
        day = f"{days:02d}:"
    if hours or day:
        hour = f"{hours:02d}:"
    minutes = f"{minutes:02d}:"
    sec = f"{seconds:02d}"
    return f"{day}{hour}{minutes}{sec}"


class Queue:
    """A queue, useful for coordinating producer and consumer coroutines.

    If maxsize is less than or equal to zero, the queue size is infinite. If it
    is an integer greater than 0, then "await put()" will block when the
    queue reaches maxsize, until an item is removed by get().

    Unlike the standard library Queue, you can reliably know this Queue's size
    with qsize(), since your single-threaded asyncio application won't be
    interrupted between calling qsize() and doing an operation on the Queue.
    """

    _queue: collections.deque[T]

    def __init__(self, maxsize=0, *, loop=None):
        if loop is None:
            self._loop = events.get_event_loop()
        else:
            self._loop = loop
            warnings.warn(
                "The loop argument is deprecated since Python 3.8, and scheduled for removal in Python 3.10.",
                DeprecationWarning,
                stacklevel=2,
            )
        self._maxsize = maxsize

        # Futures.
        self._getters = collections.deque()
        # Futures.
        self._putters = collections.deque()
        self._unfinished_tasks = 0
        self._finished = locks.Event(loop=loop)
        self._finished.set()
        self._init(maxsize)

    @property
    def raw_queue(self):
        return self._queue.copy()

    @raw_queue.setter
    def raw_queue(self, value: collections.deque[T]):
        if not isinstance(value, collections.deque):
            raise TypeError("Queue value must be a collections.deque[AudioTrack]")
        if len(value) >= self._maxsize:
            raise ValueError(f"Queue value cannot be longer than maxsize: {self._maxsize}")
        self._queue = value

    async def popindex(self, index: int) -> T:
        value = self._queue[index]
        del self._queue[index]
        return value

    async def remove(self, value: T) -> None:
        try:
            self._queue.remove(value)
            with contextlib.suppress(ValueError):
                while value in self:
                    self._queue.remove(value)
        except ValueError:
            raise IndexError("Value not in queue")

    # These three are overridable in subclasses.

    def _init(self, maxsize: int):
        self._queue = collections.deque(maxlen=maxsize or None)

    def _get(self, index: int = None) -> T:
        if index is not None:
            return self.popindex(index)
        else:
            return self._queue.popleft()

    def _put(self, items: list[T], index: int = None):
        if index is not None:
            if index < 0:
                for i in items:
                    self._queue.append(i)
            else:
                for i in items:
                    self._queue.insert(index, i)
                    index += 1
        else:
            self._queue.extendleft(items)

    # End of the overridable methods.

    def _wakeup_next(self, waiters):
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

    @property
    def maxsize(self) -> int:
        """Number of items allowed in the queue."""
        return self._maxsize

    def empty(self) -> bool:
        """Return True if the queue is empty, False otherwise."""
        return not self._queue

    def full(self) -> bool:
        """Return True if there are maxsize items in the queue.

        Note: if the Queue was initialized with maxsize=0 (the default),
        then full() is never True.
        """
        if self._maxsize <= 0:
            return False
        else:
            return self.qsize() >= self._maxsize

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

    def clear(self):
        """Remove all items from the queue."""
        self._getters.clear()
        self._putters.clear()
        self._queue.clear()

    async def shuffle(self):
        """Shuffle the queue."""
        if self.empty():
            return
        await asyncio.to_thread(random.shuffle, self._queue)

    def __contains__(self, obj: T) -> bool:
        return obj in self._queue

    def __len__(self):
        return self.qsize()


class LifoQueue(Queue[T]):
    def __int__(self, maxsize: int = 0) -> None:
        super().__init__(maxsize=maxsize)

    def _put(self, items: list[T], index: int = None):
        if self.full():
            for i in range(len(items)):
                self._queue.popleft()
        if index is not None:
            if index < 0:
                for i in items:
                    self._queue.appendleft(i)
            else:
                for i in items:
                    self._queue.insert(index, i)
                    index += 1
        else:
            self._queue.extend(items)

    def _get(self, index: int = None) -> T:
        if index is not None:
            return self.popindex(index)
        else:
            return self._queue.pop()

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
