"""
This module contains various utilities for working with asyncio taken from
https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/core/utils/predicates.py
https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/core/utils/__init__.py

Original license can be found at:
https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/LICENSE
"""
from __future__ import annotations

import asyncio
import re
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Coroutine,
    Generator,
    Iterable,
    Iterator,
    Sequence,
)
from itertools import chain
from re import Pattern
from typing import Any, TypeVar, cast

import discord
from discord.ext import commands

from pylav.constants.regex import DISCORD_CHANNEL_MENTION, DISCORD_ID, DISCORD_ROLE_MENTION, DISCORD_USER_MENTION

_T = TypeVar("_T")
_S = TypeVar("_S")

# https://github.com/PyCQA/pylint/issues/2717


# Benchmarked to be the fastest method.
def deduplicate_iterables(*iterables: Iterable[_T]) -> list[_T]:
    """
    Returns a list of all unique items in ``iterables``, in the order they
    were first encountered.
    """
    # dict insertion order is guaranteed to be preserved in 3.6+
    return list(dict.fromkeys(chain.from_iterable(iterables)))


# https://github.com/PyCQA/pylint/issues/2717
class AsyncFilter(AsyncIterator[_T], Awaitable[list[_T]]):  # pylint: disable=duplicate-bases
    """Class returned by `async_filter`. See that function for details.

    We do not recommend instantiating this class directly.
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

    def __aiter__(self) -> AsyncFilter[_T]:
        return self

    def __await__(self) -> Generator[Any, None, list[_T]]:
        # Simply return the generator filled into a list
        return self.__flatten().__await__()

    def __anext__(self) -> Coroutine[Any, Any, _T]:
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


async def _sem_wrapper(sem: asyncio.Semaphore, task: Awaitable[_T] | asyncio.Future) -> _T:
    async with sem:
        return await task


def bounded_gather_iter(
    *coros_or_futures: Awaitable[_T] | asyncio.Future, limit: int = 4, semaphore: asyncio.Semaphore | None = None
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
        # noinspection PyProtectedMember
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
    >>> from pylav.utils.vendor.redbot import AsyncIter
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
        return await discord.utils.maybe_coroutine(self._map, item) if self._map is not None else item

    def __await__(self) -> Generator[Any, None, list[_T]]:
        """Returns a list of the iterable.

        Examples
        --------
        >>> from pylav.utils.vendor.redbot import AsyncIter
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
        >>> from pylav.utils.vendor.redbot import AsyncIter
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
        >>> from pylav.utils.vendor.redbot import AsyncIter
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
        >>> from pylav.utils.vendor.redbot import AsyncIter
        >>> def predicate(value):
        ...     return value <= 5
        >>> iterator = AsyncIter([1, 10, 5, 100])
        >>> async for i in iterator.filter(predicate):
        ...     print(i)
        1
        5

        >>> from pylav.utils.vendor.redbot import AsyncIter
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
        >>> from pylav.utils.vendor.redbot import AsyncIter
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
        >>> from pylav.utils.vendor.redbot import AsyncIter
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
        >>> from pylav.utils.vendor.redbot import AsyncIter
        >>> await AsyncIter(range(3)).find(lambda x: x == 1)
        1
        """
        while True:
            try:
                elem = await self.__anext__()
            except StopAsyncIteration:
                return default
            ret = await discord.utils.maybe_coroutine(predicate, elem)
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
        >>> from pylav.utils.vendor.redbot import AsyncIter
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

            match = DISCORD_ID.match(m.content) or DISCORD_USER_MENTION.match(m.content)
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

            match = DISCORD_ID.match(m.content) or DISCORD_CHANNEL_MENTION.match(m.content)
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
            if match := pattern_obj.search(m.content):
                self.result = match
                return True
            return False

        return cls(predicate)

    @staticmethod
    def _find_role(guild: discord.Guild, argument: str) -> discord.Role | None:
        return (
            guild.get_role(int(match.group(1)))
            if (match := DISCORD_ID.match(argument) or DISCORD_ROLE_MENTION.match(argument))
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
