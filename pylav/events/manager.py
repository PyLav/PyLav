from __future__ import annotations

import inspect

from pylav.events import base, node, player, queue, track
from pylav.events.utils import get_event_name


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

        self._client = client
        self.dispatcher = client.bot.dispatch

        self.mapping: dict[type[base.PyLavEvent], str] = {}
        self._build_mapper(player)
        self._build_mapper(node)
        self._build_mapper(queue)
        self._build_mapper(track)

    def _build_mapper(self, module: node | player | queue | track) -> None:  # type: ignore
        self.mapping.update(
            {
                c: get_event_name(c)
                for _, c in inspect.getmembers(module, inspect.isclass)
                if issubclass(c, base.PyLavEvent)
            }
        )

    async def dispatch(self, event: base.PyLavEvent) -> None:
        event_name = self.mapping[type(event)]
        self.dispatcher(event_name, event)

    def get_event_names(self) -> set[str]:
        return set(self.mapping.values())
