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

    Event can be listened to by adding a listener with the name `pylav_track_stuck_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that is stuck.
    track: :class:`Track`
        The track that is stuck.
    threshold: :class:`int`
        The threshold in milliseconds.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStuck`
        The raw event object.

    """

    __slots__ = ("player", "track", "threshold", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStuck):
        self.player = player
        self.track = track
        self.threshold = event_object.thresholdMs
        self.node = node
        self.event = event_object


class TrackExceptionEvent(PyLavEvent):
    """This event is dispatched when an exception occurs while playing a track.

    Event can be listened to by adding a listener with the name `pylav_track_exception_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that encountered the exception.
    track: :class:`Track`
        The track that encountered the exception.
    exception: :class:`str`
        The exception that was encountered.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackException`
        The raw event object.
    """

    __slots__ = ("player", "track", "exception", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackException):
        self.player = player
        self.track = track
        self.exception = event_object.exception.cause
        self.node = node
        self.event = event_object


class TrackEndEvent(PyLavEvent):
    """This event is dispatched when the player finished playing a track.

    Event can be listened to by adding a listener with the name `pylav_track_end_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that finished playing the track.
    track: :class:`Track`
        The track that finished playing.
    reason: :class:`str`
        The reason why the track finished playing.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackEnd`
        The raw event object.

    """

    __slots__ = ("player", "track", "reason", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackEnd) -> None:
        self.player = player
        self.track = track
        self.reason = event_object.reason
        self.node = node
        self.event = event_object


class TrackAutoPlayEvent(PyLavEvent):
    """This event is dispatched when the player starts to play a track.

    Event can be listened to by adding a listener with the name `pylav_track_start_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started playing the track.
    track: :class:`Track`
        The track that started playing.

    """

    __slots__ = ("player", "track")

    def __init__(self, player: Player, track: Track) -> None:
        self.player = player
        self.track = track


class TrackResumedEvent(PyLavEvent):
    """This event is dispatched when the player resumes playing a track.

    Event can be listened to by adding a listener with the name `pylav_track_resume_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that resumed playing the track.
    track: :class:`Track`
        The track that resumed playing.
    requester: :class:`discord.Member`
        The member that requested the resume.

    """

    __slots__ = ("player", "track", "requester")

    def __init__(self, player: Player, track: Track, requester: discord.Member) -> None:
        self.player = player
        self.track = track
        self.requester = requester


class TrackSeekEvent(PyLavEvent):
    """This event is dispatched when the player is moved.

    Event can be listened to by adding a listener with the name `pylav_track_seek_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that moved.
    track: :class:`Track`
        The track that was moved.
    requester: :class:`discord.Member`
        The member that requested the move.
    before: :class:`float`
        The position before the move.
    after: :class:`float`
        The position after the move.

    """

    __slots__ = ("player", "track", "requester", "before", "after")

    def __init__(self, player: Player, requester: discord.Member, track: Track, before: float, after: float) -> None:
        self.player = player
        self.requester = requester
        self.track = track
        self.before = before
        self.after = after


class TrackPreviousRequestedEvent(PyLavEvent):
    """This event is dispatched when a history track is requested.

    Event can be listened to by adding a listener with the name `pylav_track_previous_requested_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that requested the track.
    track: :class:`Track`
        The track that was requested.
    requester: :class:`discord.Member`
        The member that requested the track.

    """

    __slots__ = ("player", "track", "requester")

    def __init__(self, player: Player, requester: discord.Member, track: Track) -> None:
        self.player = player
        self.requester = requester
        self.track = track


class TrackSkippedEvent(PyLavEvent):
    """This event is dispatched when a track is skipped.

    Event can be listened to by adding a listener with the name `pylav_track_skipped_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that skipped the track.
    track: :class:`Track`
        The track that was skipped.
    requester: :class:`discord.Member`
        The member that requested the skip.

    """

    __slots__ = ("player", "track", "requester", "position")

    def __init__(self, player: Player, requester: discord.Member, track: Track, position: float) -> None:
        self.player = player
        self.track = track
        self.requester = requester
        self.position = position
