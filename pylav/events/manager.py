from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from pylav.events import api, base, node, player, plugins, queue, track
from pylav.events.plugins import sponsorblock
from pylav.events.track import track_start
from pylav.events.utils import get_event_name, get_simple_event_name

if TYPE_CHECKING:
    from pylav.core.client import Client


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
    >>> async def on_pylav_queue_end_event(self, event: queue.QueueEndEvent):
    >>>    print(f"Queue ended: {event.player.guild.name}")

    >>> @commands.Cog.listener()
    >>> async def on_pylav_track_stuck_event(self, event: track.TrackStuckEvent):
    >>>    print(f"Track got stuck: {event.track.encoded}")

    """

    __slots__ = ("_client", "dispatcher", "mapping")

    def __init__(self, client: Client) -> None:
        self._client = client
        self.dispatcher = client.bot.dispatch

        self.mapping: dict[type[base.PyLavEvent], str] = {}
        self._update_mapper(player)
        self._update_mapper(node)
        self._update_mapper(queue)
        self._update_mapper(track)
        self._update_mapper(plugins)
        self._update_mapper(track_start)
        self._update_mapper(sponsorblock)
        self._update_mapper(api)

    def _update_mapper(self, module: node | player | queue | track) -> None:  # type: ignore
        """Updates the mapping with the events from the given module."""
        self.mapping.update(
            {
                c: get_event_name(c)
                for _, c in inspect.getmembers(module, inspect.isclass)
                if issubclass(c, base.PyLavEvent) and not isinstance(c, base.PyLavEvent)
            }
        )

    async def dispatch(self, event: base.PyLavEvent) -> None:
        """Dispatches an event to the appropriate handler"""
        event_name = self.mapping[type(event)]
        self.dispatcher(event_name, event)

    def get_event_names(self) -> set[str]:
        """Returns a set of all event names

        Returns
        -------
        set[str]
            A set of all event names prefixed with `pylav_`
        """
        return set(self.mapping.values())

    def simple_event_names(self) -> set[str]:
        """Returns a set of all simple event names

        Returns
        -------
        set[str]
            A set of all event names

        """
        return {get_simple_event_name(k) for k in self.mapping.keys()}
