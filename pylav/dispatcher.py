from __future__ import annotations

import inspect
import re
from typing import TYPE_CHECKING

from pylav import events

if TYPE_CHECKING:
    from pylav.client import Client


def to_snake_case(name):
    return re.sub(
        "([a-z0-9])([A-Z])", r"\1_\2", re.sub("__([A-Z])", r"_\1", re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name))
    ).lower()


def get_event_name(c: type[events.Event]) -> str:
    return f"pylav_{to_snake_case(c.__name__)}"


class DispatchManager:
    """
    The Dispatcher is responsible for dispatching events to the appropriate
    handlers.

    The method names are the event names.

    You can listen to events by adding the following to your client:


    Examples
    --------
    >>> from discord.app_commands import commands

    >>> @commands.Cog.listener()
    >>> async def on_pylav_queue_end_event(self, event: events.QueueEndEvent):
    >>>    print(f"Queue ended: {event.player}")

    >>> @commands.Cog.listener()
    >>> async def on_pylav_track_stuck_event(self, event: events.TrackStuckEvent):
    >>>    print(f"Track got stuck: {event.track}")

    """

    __slots__ = ("_client", "dispatcher", "mapping")

    def __init__(self, client: Client):
        self._client = client
        self.dispatcher = client.bot.dispatch

        self.mapping = {
            c: get_event_name(c) for _, c in inspect.getmembers(events, inspect.isclass) if issubclass(c, events.Event)
        }

    async def dispatch(self, event: events.Event):
        event_name = self.mapping[type(event)]
        self.dispatcher(event_name, event)

    def get_event_names(self) -> set[str]:
        return set(self.mapping.values())
