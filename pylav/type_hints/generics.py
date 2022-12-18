from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, ParamSpec, Protocol, TypeVar, Union

ANY_GENERIC_TYPE = TypeVar("ANY_GENERIC_TYPE")
PARAM_SPEC_TYPE = ParamSpec("PARAM_SPEC_TYPE")

CORO_TYPE = Coroutine[Any, Any, ANY_GENERIC_TYPE]
CORO_FUNCTION = Callable[..., CORO_TYPE[Any]]
MaybeCoro = Union[ANY_GENERIC_TYPE, CORO_TYPE[ANY_GENERIC_TYPE]]
MaybeAwaitable = Union[ANY_GENERIC_TYPE, Awaitable[ANY_GENERIC_TYPE]]


class SupportsStr(Protocol):
    def __str__(self) -> str:
        ...
