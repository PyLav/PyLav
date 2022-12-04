from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from pylav.event_dispatcher.utils import get_event_name

if TYPE_CHECKING:
    from pylav.events.base import PyLavEvent
    from pylav.events.queue import QueueEndEvent
    from pylav.events.track import TrackStuckEvent


class DispatchManager:
    """
    The Dispatcher is responsible for dispatching events to the appropriate
    handlers.

    The method names are the event names.

    You can listen to events by adding the following to your client:


    Examples
    --------
    >>> from discord.ext import commands

    >>> @commands.Cog.listener()
    >>> async def on_pylav_queue_end_event(self, event: QueueEndEvent):
    >>>    print(f"Queue ended: {event.player}")

    >>> @commands.Cog.listener()
    >>> async def on_pylav_track_stuck_event(self, event: TrackStuckEvent):
    >>>    print(f"Track got stuck: {event.track}")

    """

    __slots__ = ("_client", "dispatcher", "mapping")

    def __init__(self, client: Client) -> None:
        from pylav import events
        from pylav.events.base import PyLavEvent

        self._client = client
        self.dispatcher = client.bot.dispatch

        self.mapping = {
            c: get_event_name(c) for _, c in inspect.getmembers(events, inspect.isclass) if issubclass(c, PyLavEvent)
        }

    async def dispatch(self, event: PyLavEvent) -> None:
        event_name = self.mapping[type(event)]
        self.dispatcher(event_name, event)

    def get_event_names(self) -> set[str]:
        return set(self.mapping.values())
