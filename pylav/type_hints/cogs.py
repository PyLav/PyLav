from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pylav.type_hints.bot import DISCORD_COG_TYPE, DISCORD_COMMAND_ERROR_TYPE, DISCORD_CONTEXT_TYPE
from pylav.type_hints.generics import CORO_TYPE, MaybeCoro

DISCORD_CHECK_TYPE = Callable[[DISCORD_CONTEXT_TYPE], MaybeCoro[bool]]

DISCORD_HOOK_TYPE = (
    Callable[[DISCORD_COG_TYPE, DISCORD_CONTEXT_TYPE], CORO_TYPE[Any]]
    | Callable[[DISCORD_CONTEXT_TYPE], CORO_TYPE[Any]]
)

DISCORD_ERROR_TYPE = (
    Callable[[DISCORD_COG_TYPE, DISCORD_CONTEXT_TYPE, DISCORD_COMMAND_ERROR_TYPE], CORO_TYPE[Any]]
    | Callable[[DISCORD_CONTEXT_TYPE, DISCORD_COMMAND_ERROR_TYPE], CORO_TYPE[Any]],
)
