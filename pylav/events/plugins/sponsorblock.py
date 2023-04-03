from __future__ import annotations

from typing import TYPE_CHECKING

from pylav.events.base import PyLavEvent
from pylav.nodes.api.responses.plugins import SegmentSkipped, SegmentsLoaded

__all__ = ("SegmentSkippedEvent", "SegmentsLoadedEvent")

if TYPE_CHECKING:
    from pylav.nodes.node import Node
    from pylav.players.player import Player


class SegmentSkippedEvent(PyLavEvent):
    """This event is dispatched when a segment is skipped.

    Event can be listened to by adding a listener with the name `pylav_segment_skipped_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that skipped the segment.
    segment: :class:`Segment`
        The segment that was skipped.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`SegmentSkipped`
        The raw event object.

    """

    __slots__ = ("player", "segment", "node", "event")

    def __init__(self, player: Player, node: Node, event_object: SegmentSkipped) -> None:
        self.player = player
        self.segment = event_object.segment
        self.node = node
        self.event = event_object


class SegmentsLoadedEvent(PyLavEvent):
    """This event is dispatched when segments are loaded.

    Event can be listened to by adding a listener with the name `pylav_segments_loaded_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that loaded the segments.
    segments: :class:`list[Segment]`
        The segments that were loaded.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`SegmentsLoaded`
        The raw event object.

    """

    __slots__ = ("player", "segments", "node", "event")

    def __init__(self, player: Player, node: Node, event_object: SegmentsLoaded) -> None:
        self.player = player
        self.segments = event_object.segments
        self.node = node
        self.event = event_object
