from __future__ import annotations

import collections
from typing import TYPE_CHECKING, Literal

import discord

from pylav.filters import ChannelMix, Distortion, Equalizer, Karaoke, LowPass, Rotation, Timescale, Vibrato, Volume
from pylav.filters.tremolo import Tremolo
from pylav.utils import Segment

if TYPE_CHECKING:
    from pylav.node import Node
    from pylav.player import Player
    from pylav.tracks import AudioTrack


class Event:
    """The base for all Lavalink events."""


class QueueEndEvent(Event):
    """
    This event is dispatched when there are no more songs in the queue.
    Attributes
    ----------
    player: :class:`Player`
        The player that has no more songs in queue.
    """

    __slots__ = ("player",)

    def __init__(self, player: Player):
        self.player = player


class TrackStuckEvent(Event):
    """
    This event is dispatched when the currently playing track is stuck.
    This normally has something to do with the stream you are playing
    and not Lavalink itself.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that has the playing track being stuck.
    track: :class:`AudioTrack`
        The track is stuck from playing.
    threshold: :class:`int`
        The amount of time the track had while being stuck.
    """

    __slots__ = ("player", "track", "threshold")

    def __init__(self, player: Player, track: AudioTrack, threshold: float):
        self.player = player
        self.track = track
        self.threshold = threshold


class TrackExceptionEvent(Event):
    """
    This event is dispatched when an exception occurs while playing a track.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that had the exception occur while playing a track.
    track: :class:`AudioTrack`
        The track that had the exception while playing.
    exception: :class:`Exception`
        The type of exception that the track had while playing.
    """

    __slots__ = ("player", "track", "exception")

    def __init__(self, player: Player, track: AudioTrack, exception: Exception):
        self.player = player
        self.track = track
        self.exception = exception


class TrackEndEvent(Event):
    """
    This event is dispatched when the player finished playing a track.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that finished playing a track.
    track: :class:`AudioTrack`
        The track that finished playing.
    reason: :class:`str`
        The reason why the track stopped playing.
    """

    __slots__ = ("player", "track", "reason")

    def __init__(self, player: Player, track: AudioTrack, reason: str):
        self.player = player
        self.track = track
        self.reason = reason


class TrackStartEvent(Event):
    """
    This event is dispatched when the player starts to play a track.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that started to play a track.
    track: :class:`AudioTrack`
        The track that started playing.
    """

    __slots__ = ("player", "track")

    def __init__(self, player: Player, track: AudioTrack):
        self.player = player
        self.track = track


class PlayerUpdateEvent(Event):
    """
    This event is dispatched when the player's progress changes.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that's progress was updated.
    position: :class:`int`
        The position of the player that was changed to.
    timestamp: :class:`int`
        The timestamp that the player is currently on.
    """

    __slots__ = ("player", "position", "timestamp")

    def __init__(self, player: Player, position: float, timestamp: float):
        self.player = player
        self.position = position
        self.timestamp = timestamp


class NodeDisconnectedEvent(Event):
    """
    This event is dispatched when a node disconnects and becomes unavailable.
    Attributes
    ----------
    node: :class:`Node`
        The node that was disconnected from.
    code: :class:`int`
        The status code of the event.
    reason: :class:`str`
        The reason of why the node was disconnected.
    """

    __slots__ = ("node", "code", "reason")

    def __init__(self, node: Node, code: int, reason: str):
        self.node = node
        self.code = code
        self.reason = reason


class NodeConnectedEvent(Event):
    """
    This event is dispatched when Lavalink.py successfully connects to a node.
    Attributes
    ----------
    node: :class:`Node`
        The node that was successfully connected to.
    """

    __slots__ = ("node",)

    def __init__(self, node: Node):
        self.node = node


class NodeChangedEvent(Event):
    """
    This event is dispatched when a player changes to another node.
    Keep in mind this event can be dispatched multiple times if a node
    disconnects and the load balancer moves players to a new node.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose node was changed.
    old_node: :class:`Node`
        The node the player was moved from.
    new_node: :class:`Node`
        The node the player was moved to.
    """

    __slots__ = ("player", "old_node", "new_node")

    def __init__(self, player: Player, old_node: Node, new_node: Node):
        self.player = player
        self.old_node = old_node
        self.new_node = new_node


class WebSocketClosedEvent(Event):
    """
    This event is dispatched when an audio websocket to Discord
    is closed. This can happen for various reasons like an
    expired voice server update.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose audio websocket was closed.
    code: :class:`int`
        The node the player was moved from.
    reason: :class:`str`
        The node the player was moved to.
    by_remote: :class:`bool`
        If the websocket was closed remotely.
    """

    __slots__ = ("player", "code", "reason", "by_remote")

    def __init__(self, player: Player, code: int, reason: str, by_remote: bool):
        self.player = player
        self.code = code
        self.reason = reason
        self.by_remote = by_remote


class SegmentSkippedEvent(Event):
    """
    This event is dispatched when a segment is skipped.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose segment was skipped.
    """

    __slots__ = ("player", "category", "start", "end")

    def __init__(self, player: Player, category: str, start: float, end: float):
        self.player = player
        self.segment = Segment(category=category, start=start, end=end)


class SegmentsLoadedEvent(Event):
    """
    This event is dispatched when segments are loaded.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose segments were loaded.
    segments: :class:`list` of :class:`Segment`
        The segments that were loaded.
    """

    __slots__ = ("player", "segments")

    def __init__(self, player: Player, segments: list[dict]):
        self.player = player
        self.segments = [Segment(**segment) for segment in segments]


class PlayerPausedEvent(Event):
    """
    This event is dispatched when a player is paused.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose track was paused.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member):
        self.player = player
        self.user = requester


class PlayerStoppedEvent(Event):
    """
    This event is dispatched when a player is stopped.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player which was stopped.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member):
        self.player = player
        self.requester = requester


class PlayerResumedEvent(Event):
    """
    This event is dispatched when a player is resumed.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose track was resumed.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "track", "requester")

    def __init__(self, player: Player, requester: discord.Member):
        self.player = player
        self.requester = requester


class TrackQueuePositionChangedEvent(Event):
    """
    This event is dispatched when the position of a track is changed.
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
    track: :class:`AudioTrack`
        The track whose position was changed.
    """

    __slots__ = ("player", "before", "after", "requester", "track")

    def __init__(self, player: Player, before: int, after: int, requester: discord.Member, track: AudioTrack):
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after
        self.track = track


class TrackSkippedEvent(Event):
    """
    This event is dispatched when a track is skipped.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose track was skipped.
    track: :class:`AudioTrack`
        The track that was skipped.
    requester: :class:`discord.Member`
        The user who requested the change.
    position: :class:`float`
        The position of the track before the skip.
    """

    __slots__ = ("player", "track", "requester")

    def __init__(self, player: Player, requester: discord.Member, track: AudioTrack, position: float):
        self.player = player
        self.track = track
        self.requester = requester
        self.position = position


class QueueShuffledEvent(Event):
    """
    This event is dispatched when the queue is shuffled.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member):
        self.player = player
        self.requester = requester


class TracksRemovedFromQueueEvent(Event):
    """
    This event is dispatched when tracks are removed from the queue.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "requester", "tracks")

    def __init__(self, player: Player, requester: discord.Member, tracks: list[AudioTrack]):
        self.player = player
        self.requester = requester
        self.tracks = tracks


class FiltersAppliedEvent(Event):
    """
    This event is dispatched when filters are applied.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.

    """

    __slots__ = (
        "player",
        "requester",
        "requester",
        "volume",
        "equalizer",
        "karaoke",
        "timescale",
        "tremolo",
        "vibrato",
        "rotation",
        "distortion",
        "low_pass",
        "channel_mix",
    )

    def __init__(
        self,
        player: Player,
        requester: discord.Member,
        volume: Volume = None,
        equalizer: Equalizer = None,
        karaoke: Karaoke = None,
        timescale: Timescale = None,
        tremolo: Tremolo = None,
        vibrato: Vibrato = None,
        rotation: Rotation = None,
        distortion: Distortion = None,
        low_pass: LowPass = None,
        channel_mix: ChannelMix = None,
    ):
        self.player = player
        self.requester = requester
        self.volume = volume
        self.equalizer = equalizer
        self.karaoke = karaoke
        self.timescale = timescale
        self.tremolo = tremolo
        self.vibrato = vibrato
        self.rotation = rotation
        self.distortion = distortion
        self.low_pass = low_pass
        self.channel_mix = channel_mix


class PlayerMovedEvent(Event):
    """
    This event is dispatched when the player is moved.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.

    """

    __slots__ = ("player", "requester", "before", "after")

    def __init__(
        self, player: Player, requester: discord.Member, before: discord.VoiceChannel, after: discord.VoiceChannel
    ):
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after


class PlayerDisconnectedEvent(Event):
    """
    This event is dispatched when the player is moved.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.


    """

    __slots__ = ("player", "requester", "current_track", "position", "queue")

    def __init__(self, player: Player, requester: discord.Member):
        self.player = player
        self.requester = requester
        self.current_track: AudioTrack | None = player.current
        self.position: float = player.position
        self.queue: collections.deque = player.queue.raw_queue


class PlayerConnectedEvent(Event):
    """
    This event is dispatched when the player is moved.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.


    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member | None):
        self.player = player
        self.requester = requester


class TrackSeekEvent(Event):
    """
    This event is dispatched when the player is moved.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    track: :class:`AudioTrack`
        The track that was seeked.
    after: float
        The position in the track that was seeked to.
    before: float
        The position in the track that was seeked from.

    """

    __slots__ = ("player", "requester", "track", "position")

    def __init__(self, player: Player, requester: discord.Member, track: AudioTrack, before: float, after: float):
        self.player = player
        self.requester = requester
        self.track = track
        self.before = before
        self.after = after


class PlayerVolumeChangeEvent(Event):
    """
    This event is dispatched when the player is moved.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    before: float
        The volume before the change.
    after: float
        The volume after the change.

    """

    __slots__ = ("player", "requester", "before", "after")

    def __init__(self, player: Player, requester: discord.Member, before: int, after: int):
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after


class PlayerRepeatEvent(Event):
    """
    This event is dispatched when the player is moved.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    queue_before: bool
        The repeat state before the change.
    queue_after: bool
        The repeat state after the change.
    current_before: bool
        The repeat state before the change.
    current_after: bool
        The repeat state after the change.
    type : str
        The type of repeat that was set.

    """

    __slots__ = ("player", "requester", "queue_before", "queue_after", "current_before", "current_after", "type")

    def __init__(
        self,
        player: Player,
        requester: discord.Member,
        op_type: Literal["current", "queue"],
        queue_before: bool,
        queue_after: bool,
        current_before: bool,
        current_after: bool,
    ):
        self.player = player
        self.requester = requester
        self.queue_before = queue_before
        self.queue_after = queue_after
        self.current_before = current_before
        self.current_after = current_after
        self.type = op_type


class PreviousTrackRequestedEvent(Event):
    """
    This event is dispatched when a history track is requested.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    track: :class:`AudioTrack`
        The track that was seeked.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member, track: AudioTrack):
        self.player = player
        self.requester = requester
        self.track = track


class TracksRequestedEvent(Event):
    """
    This event is dispatched when a track in added to the queue.
    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    tracks: List[:class:`AudioTrack`]
        The track that was seeked.
    """

    __slots__ = ("player", "requester", "tracks")

    def __init__(self, player: Player, requester: discord.Member, tracks: list[AudioTrack]):
        self.player = player
        self.requester = requester
        self.tracks = tracks
