from __future__ import annotations

from typing import TYPE_CHECKING

from pylav.events.base import PyLavEvent

if TYPE_CHECKING:
    from pylav.nodes.api.responses.rest_api import LoadTrackResponses
    from pylav.nodes.node import Node


class LavalinkLoadtracksEvent(PyLavEvent):
    """This event is dispatched when the Lavalink /loadtracks endpoint is called.

    Event can be listened to by adding a listener with the name `pylav_lavalink_loadtracks_event`.

    Attributes
    ----------
    node: :class:`Node`
        The node that called the endpoint.

    Parameters
    ----------
    player: :class:`Player`
        The player that has no more songs in queue.
    response: :class:`LoadTrackResponses`
        The response from the endpoint.
    """

    __slots__ = ("player", "response")

    def __init__(self, node: Node, response: LoadTrackResponses) -> None:
        self.node = node
        self.response = response
