from __future__ import annotations

from typing import TYPE_CHECKING

from pylav.events.base import PyLavEvent
from pylav.nodes.api.responses.plugins import SegmentSkipped, SegmentsLoaded

__all__ = ("SegmentSkippedEvent", "SegmentsLoadedEvent")

if TYPE_CHECKING:
    from pylav.nodes.node import Node
    from pylav.players.player import Player


class SegmentSkippedEvent(PyLavEvent):
    """This event is dispatched when a segment is skipped."""

    __slots__ = ()

    def __init__(self, player: Player, node: Node, event_object: SegmentSkipped) -> None:
        self.player = player
        self.segment = event_object.segment
        self.node = node
        self.event = event_object


class SegmentsLoadedEvent(PyLavEvent):
    """This event is dispatched when segments are loaded."""

    __slots__ = ()

    def __init__(self, player: Player, node: Node, event_object: SegmentsLoaded) -> None:
        self.player = player
        self.segments = event_object.segments
        self.node = node
        self.event = event_object
