from __future__ import annotations

import asyncio
import collections
import contextlib
import random
import threading
from abc import ABC
from asyncio import Event, QueueFull, get_event_loop
from collections.abc import Iterator
from types import GenericAlias
from typing import NoReturn

from pylav.type_hints.generics import ANY_GENERIC_TYPE


class PlayerQueue(asyncio.Queue[ANY_GENERIC_TYPE]):
    """A queue, useful for coordinating producer and consumer coroutines.

    If maxsize is less than or equal to zero, the queue size is infinite. If it
    is an integer greater than 0, then "await put()" will block when the
    queue reaches maxsize, until an item is removed by get().

    Unlike the standard library Queue, you can reliably know this Queue's size
    with qsize(), since your single-threaded asyncio application won't be
    interrupted between calling qsize() and doing an operation on the Queue.
    """

    __slots__ = ("_queue", "_maxsize", "_getters", "_putters", "_unfinished_tasks", "_finished", "_loop")

    _queue: collections.deque[ANY_GENERIC_TYPE]
    raw_b64s: list[str]

    def __init__(self, maxsize: int = 0) -> None:
        self._lock = asyncio.Lock()
        self._threading_lock = threading.Lock()
        super().__init__(maxsize=maxsize)
        self._maxsize = maxsize
        self._loop = get_event_loop()

        # Futures.
        self._getters: collections.deque[asyncio.Future] = collections.deque()
        # Futures.
        self._putters: collections.deque[asyncio.Future] = collections.deque()
        self._unfinished_tasks = 0
        self._finished = Event()
        self._finished.set()
        self._init(maxsize)

    # These do not exist in asyncio.Queue
    @property
    def raw_queue(self) -> collections.deque[ANY_GENERIC_TYPE]:
        return self._queue.copy()

    @raw_queue.setter
    def raw_queue(self, value: collections.deque[ANY_GENERIC_TYPE]):
        if not isinstance(value, collections.deque):
            raise TypeError("Queue value must be a collections.deque[Track]")
        if self._maxsize and len(value) > self._maxsize:
            raise ValueError(f"Queue value cannot be longer than maxsize: {self._maxsize}")
        self._queue = value

    @raw_queue.deleter
    def raw_queue(self) -> None:
        self.clear()

    def popindex(self, index: int) -> ANY_GENERIC_TYPE:
        with self._threading_lock:
            value = self._queue[index]
            del self._queue[index]
            return value

    async def remove(self, value: ANY_GENERIC_TYPE, duplicates: bool = False) -> tuple[list[ANY_GENERIC_TYPE], int]:
        """Removes the first occurrence of a value from the queue.

        If duplicates is True, all occurrences of the value are removed.
        Returns the removed entries and number of occurrences removed.
        """
        async with self._lock:
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

    def clear(self) -> None:
        """Remove all items from the queue"""
        with self._threading_lock:
            self._queue.clear()
            for i in self._getters:
                i.cancel()
            self._getters.clear()
            for i in self._putters:
                i.cancel()
            self._putters.clear()

    async def shuffle(self) -> None:
        """Shuffle the queue"""
        async with self._lock:
            if self.empty():
                return
            await asyncio.to_thread(random.shuffle, self._queue)

    async def get_oldest(self) -> ANY_GENERIC_TYPE:
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
        return self.get_nowait(index=-1)

    def index(self, value: ANY_GENERIC_TYPE) -> int:
        """Return first index of value"""
        return self._queue.index(value)

    def __contains__(self, obj: ANY_GENERIC_TYPE) -> bool:
        return obj in self._queue

    def __iter__(self) -> Iterator[ANY_GENERIC_TYPE]:
        return iter(self.raw_queue)

    def __len__(self) -> int:
        return len(self._queue)

    def __index__(self) -> int:
        return len(self._queue)

    def __getitem__(self, key: int | slice) -> ANY_GENERIC_TYPE | list[ANY_GENERIC_TYPE]:
        return self.raw_queue[key]

    def __setitem__(self, key: int, value: ANY_GENERIC_TYPE | list[ANY_GENERIC_TYPE]) -> NoReturn:
        raise NotImplementedError("Use .put() to add entries to the queue")

    def __delitem__(self, key: int) -> NoReturn:
        raise NotImplementedError("Use .get() to remove entries from the queue")

    def __length_hint__(self) -> int:
        return len(self._queue)

    # These three are overridable in subclasses.

    def _init(self, maxsize: int) -> None:
        self._queue = collections.deque(maxlen=maxsize or None)
        self.raw_b64s = []

    def _get(self, index: int = None) -> ANY_GENERIC_TYPE:
        if index is not None:
            r = self.popindex(index)
        else:
            with self._threading_lock:
                r = self._queue.popleft()
        if r.encoded:
            self.raw_b64s.remove(r.encoded)
        return r

    def _put(self, items: list[ANY_GENERIC_TYPE], index: int = None) -> None:
        with self._threading_lock:
            if index is not None:
                for i in items:
                    if index < 0:
                        self._queue.append(i)
                        if i.encoded:
                            self.raw_b64s.append(i.encoded)
                    else:
                        self._queue.insert(index, i)
                        if i.encoded:
                            self.raw_b64s.append(i.encoded)
                        index += 1
            else:
                self._queue.extend(items)
                self.raw_b64s.extend([i.encoded for i in items if i.encoded])

    # End of the overridable methods.

    @staticmethod
    def _wakeup_next(waiters: collections.deque[asyncio.Future]) -> None:
        # Wake up the next waiter (if any) that isn't cancelled.
        while waiters:
            waiter = waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    def __repr__(self) -> str:
        return f"<{type(self).__name__} at {id(self):#x} {self._format()}>"

    def __str__(self) -> str:
        return f"<{type(self).__name__} {self._format()}>"

    __class_getitem__ = classmethod(GenericAlias)

    def _format(self) -> str:
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

    async def put(self, items: list[ANY_GENERIC_TYPE], index: int = None, discard: bool = False) -> None:
        """Put an item into the queue.

        Put an item into the queue. If the queue is full, wait until a free
        slot is available before adding item.
        """
        if discard:
            while self.full():
                await self.get_oldest()
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

    def put_nowait(self, items: list[ANY_GENERIC_TYPE], index: int = None) -> None:
        """Put an item into the queue without blocking.

        If no free slot is immediately available, raise QueueFull.
        """
        if self.full():
            raise QueueFull
        self._put(items, index=index)
        self._unfinished_tasks += 1
        self._finished.clear()
        self._wakeup_next(self._getters)

    async def get(self, index: int = None) -> ANY_GENERIC_TYPE:
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

    def get_nowait(self, index: int = None) -> ANY_GENERIC_TYPE:
        """Remove and return an item from the queue.

        Return an item if one is immediately available, else raise QueueEmpty.
        """
        if self.empty():
            return None
        item = self._get(index=index)
        self._wakeup_next(self._putters)
        return item

    def task_done(self) -> None:
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

    async def join(self) -> None:
        """Block until all items in the queue have been gotten and processed.

        The count of unfinished tasks goes up whenever an item is added to the
        queue. The count goes down whenever a consumer calls task_done() to
        indicate that the item was retrieved and all work on it is complete.
        When the count of unfinished tasks drops to zero, join() unblocks.
        """
        if self._unfinished_tasks > 0:
            await self._finished.wait()


class TrackHistoryQueue(PlayerQueue[ANY_GENERIC_TYPE], ABC):
    __slots__ = ("_queue", "_maxsize", "_getters", "_putters", "_unfinished_tasks", "_finished", "_loop")

    def __int__(self, maxsize: int = 0) -> None:
        super().__init__(maxsize=maxsize)

    def _init(self, maxsize: int) -> None:
        super()._init(maxsize)

    def _put(self, items: list[ANY_GENERIC_TYPE], index: int = None) -> None:
        with self._threading_lock:
            if len(items) + self.qsize() > self.maxsize:
                diff = len(items) + self.qsize() - self.maxsize
                for _ in range(diff):
                    self._queue.pop()
                    self.raw_b64s.pop()
            if index is not None:
                for i in items:
                    i.timestamp = 0
                    if index < 0:
                        self._queue.append(i)
                        self.raw_b64s.append(i.encoded)
                    else:
                        self._queue.insert(index, i)
                        self.raw_b64s.insert(index, i.encoded)
                        index += 1
            else:
                self._queue.extendleft(items)
                for i, t in enumerate(items):
                    t.timestamp = 0
                    self.raw_b64s.insert(i, t.encoded)

    def _get(self, index: int = None) -> ANY_GENERIC_TYPE:
        if index is not None:
            r = self.popindex(index)
            self.raw_b64s.pop(index)
        else:
            with self._threading_lock:
                r = self._queue.popleft()
                self.raw_b64s.pop()
        return r

    def put_nowait(self, items: list[ANY_GENERIC_TYPE], index: int = None) -> None:
        """Put an item into the queue without blocking.

        If no free slot is immediately available, raise QueueFull.
        """
        self._put(items, index=index)
        self._unfinished_tasks += 1
        self._finished.clear()
        self._wakeup_next(self._getters)

    def get_nowait(self, index: int = None) -> ANY_GENERIC_TYPE | None:
        """Remove and return an item from the queue.

        Return an item if one is immediately available, else raise QueueEmpty.
        """
        if self.empty():
            return None
        item = self._get(index=index)
        self._wakeup_next(self._putters)
        return item
