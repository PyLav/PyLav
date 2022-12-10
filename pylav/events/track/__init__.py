from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from pylav.events.base import PyLavEvent
from pylav.events.track.track_start import TrackStartEvent as TrackStartEvent
from pylav.nodes.api.responses.websocket import TrackEnd, TrackException, TrackStuck

if TYPE_CHECKING:
    from pylav.nodes.node import Node
    from pylav.players.player import Player
    from pylav.players.tracks.obj import Track


class TrackStuckEvent(PyLavEvent):
    """This event is dispatched when the currently playing track is stuck.
    This normally has something to do with the stream you are playing
    and not Lavalink itself.
    """

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStuck):
        self.player = player
        self.track = track
        self.threshold = event_object.thresholdMs
        self.node = node
        self.event = event_object


class TrackExceptionEvent(PyLavEvent):
    """This event is dispatched when an exception occurs while playing a track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackException):
        self.player = player
        self.track = track
        self.exception = event_object.exception.cause
        self.node = node
        self.event = event_object


class TrackEndEvent(PyLavEvent):
    """This event is dispatched when the player finished playing a track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackEnd) -> None:
        self.player = player
        self.track = track
        self.reason = event_object.reason
        self.node = node
        self.event = event_object


class TrackAutoPlayEvent(PyLavEvent):
    """This event is dispatched when the player starts to play a track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track) -> None:
        self.player = player
        self.track = track


class TrackResumedEvent(PyLavEvent):
    """This event is dispatched when the player resumes playing a track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, requester: discord.Member) -> None:
        self.player = player
        self.track = track
        self.requester = requester


class TrackSeekEvent(PyLavEvent):
    """This event is dispatched when the player is moved."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.Member, track: Track, before: float, after: float) -> None:
        self.player = player
        self.requester = requester
        self.track = track
        self.before = before
        self.after = after


class TrackPreviousRequestedEvent(PyLavEvent):
    """This event is dispatched when a history track is requested."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.Member, track: Track) -> None:
        self.player = player
        self.requester = requester
        self.track = track


class TracksRequestedEvent(PyLavEvent):
    """This event is dispatched when a track in added to the queue."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.Member, tracks: list[Track]) -> None:
        self.player = player
        self.requester = requester
        self.tracks = tracks


class TrackSkippedEvent(PyLavEvent):
    """This event is dispatched when a track is skipped."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.Member, track: Track, position: float) -> None:
        self.player = player
        self.track = track
        self.requester = requester
        self.position = position
