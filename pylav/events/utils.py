from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pylav.events.base import PyLavEvent


def to_snake_case(name: str) -> str:
    return re.sub(
        "([a-z0-9])([A-Z])", r"\1_\2", re.sub("__([A-Z])", r"_\1", re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name))
    ).lower()


def get_event_name(class_type: type[PyLavEvent]) -> str:
    return f"pylav_{to_snake_case(class_type.__name__)}"


def get_simple_event_name(class_type: type[PyLavEvent]) -> str:
    return to_snake_case(class_type.__name__)
