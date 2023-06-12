from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING

from pylav.players.filters import Echo

if TYPE_CHECKING:
    from pylav.events.base import PyLavEvent


def to_snake_case(name: str) -> str:
    """Converts a string to snake case."""

    return re.sub(
        "([a-z0-9])([A-Z])", r"\1_\2", re.sub("__([A-Z])", r"_\1", re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name))
    ).lower()


def get_event_name(class_type: type[PyLavEvent]) -> str:
    """Returns the event name for a given event class while prefixing it with `pylav_`."""
    return f"pylav_{to_snake_case(class_type.__name__)}"


def get_simple_event_name(class_type: type[PyLavEvent]) -> str:
    """Returns the event name for a given event class."""
    return to_snake_case(class_type.__name__)


@dataclasses.dataclass(eq=True, slots=True, unsafe_hash=True, kw_only=True, frozen=True)
class PluginInfoTypeHint:
    echo: Echo | None = None
