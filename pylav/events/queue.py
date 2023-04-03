from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from pylav.events.base import PyLavEvent

if TYPE_CHECKING:
    from pylav.players.player import Player
    from pylav.players.tracks.obj import Track


class QueueEndEvent(PyLavEvent):
    """This event is dispatched when there are no more songs in the queue.

    Event can be listened to by adding a listener with the name `pylav_queue_end_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that has no more songs in queue.

    Parameters
    ----------
    player: :class:`Player`
        The player that has no more songs in queue.
    """

    __slots__ = ("player",)

    def __init__(self, player: Player) -> None:
        self.player = player


class QueueTrackPositionChangedEvent(PyLavEvent):
    """This event is dispatched when the position of a track is changed.

    Event can be listened to by adding a listener with the name `pylav_queue_track_position_changed_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player whose track position was changed.
    before: :class:`int`
        The position of the track before the change.
    after: :class:`int`
        The position of the track after the change.
    requester: :class:`discord.Member`
        The user who requested the change.
    track: :class:`Track`
        The track whose position was changed.

    Parameters
    ----------
    player: :class:`Player`
        The player whose track position was changed.
    before: :class:`int`
        The position of the track before the change.
    after: :class:`int`
        The position of the track after the change.
    requester: :class:`discord.Member`
        The user who requested the change.
    track: :class:`Track`
        The track whose position was changed.
    """

    __slots__ = ("player", "before", "after", "requester", "track")

    def __init__(self, player: Player, before: int, after: int, requester: discord.Member, track: Track) -> None:
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after
        self.track = track


class QueueShuffledEvent(PyLavEvent):
    """This event is dispatched when the queue is shuffled.

    Event can be listened to by adding a listener with the name `pylav_queue_shuffled_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.

    Parameters
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member) -> None:
        self.player = player
        self.requester = requester


class QueueTracksRemovedEvent(PyLavEvent):
    """This event is dispatched when tracks are removed from the queue.

    Event can be listened to by adding a listener with the name `pylav_queue_tracks_removed_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    tracks: :class:`list` of :class:`Track`
        The tracks that were removed from the queue.

    Parameters
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    tracks: :class:`list` of :class:`Track`
        The tracks that were removed from the queue.
    """

    __slots__ = ("player", "requester", "tracks")

    def __init__(self, player: Player, requester: discord.Member, tracks: list[Track]) -> None:
        self.player = player
        self.requester = requester
        self.tracks = tracks


class QueueTracksAddedEvent(PyLavEvent):
    """This event is dispatched when a track in added to the queue.

    Event can be listened to by adding a listener with the name `pylav_queue_tracks_added_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue had tracks added to it.
    requester: :class:`discord.Member`
        The user who requested the change.
    tracks: :class:`list` of :class:`Track`
        The tracks that were added to the queue.

    """

    __slots__ = ("player", "requester", "tracks")

    def __init__(self, player: Player, requester: discord.Member, tracks: list[Track]) -> None:
        self.player = player
        self.requester = requester
        self.tracks = tracks
