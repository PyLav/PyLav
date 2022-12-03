import discord

from pylav.events.base import PyLavEvent
from pylav.events.track.track_start import TrackStartEvent


class TrackStuckEvent(PyLavEvent):
    """This event is dispatched when the currently playing track is stuck.
    This normally has something to do with the stream you are playing
    and not Lavalink itself.

    Attributes
    ----------
    player: :class:`Player`
        The player that has the playing track being stuck.
    track: :class:`Track`
        The track is stuck from playing.
    threshold: :class:`int`
        The amount of time the track had while being stuck.
    node: :class:`Node`
        The node that the track is stuck on.

    Parameters
    ----------
    player: :class:`Player`
        The player that has the playing track being stuck.
    track: :class:`Track`
        The track is stuck from playing.
    node: :class:`Node`
        The node that the stuck track is playing on.
    event_object: :class:`TrackStuckEventOpObject`
        The event object that was received from Lavalink.
    """

    __slots__ = ("player", "track", "threshold", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStuckEventOpObject):
        super().__init__()
        self.player = player
        self.track = track
        self.threshold = event_object.thresholdMs
        self.node = node
        self.event = event_object


class TrackExceptionEvent(PyLavEvent):
    """This event is dispatched when an exception occurs while playing a track.

    Attributes
    ----------
    player: :class:`Player`
        The player that had the exception occur while playing a track.
    track: :class:`Track`
        The track that had the exception while playing.
    exception: :class:`Exception`
        The type of exception that the track had while playing.
    node: :class:`Node`
        The node that the exception occurred on.

    Parameters
    ----------
    player: :class:`Player`
        The player that had the exception occur while playing a track.
    track: :class:`Track`
        The track that had the exception while playing.
    node: :class:`Node`
        The node that the exception occurred on.
    event_object: :class:`TrackExceptionEventOpObject`
        The event object that was received from Lavalink.
    """

    __slots__ = ("player", "track", "exception", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackExceptionEventOpObject):
        super().__init__()
        self.player = player
        self.track = track
        self.exception = event_object.exception.cause
        self.node = node
        self.event = event_object


class TrackEndEvent(PyLavEvent):
    """This event is dispatched when the player finished playing a track.

    Attributes
    ----------
    player: :class:`Player`
        The player that finished playing a track.
    track: :class:`Track`
        The track that finished playing.
    reason: :class:`str`
        The reason why the track stopped playing.
    node: :class:`Node`
        The node that the track finished playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that finished playing a track.
    track: :class:`Track`
        The track that finished playing.
    node: :class:`Node`
        The node that the track finished playing on.
    event_object: TrackEndEventOpObject:
        The event object that was sent from the websocket.
    """

    __slots__ = ("player", "track", "reason", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackEndEventOpObject) -> None:
        super().__init__()
        self.player = player
        self.track = track
        self.reason = event_object.reason
        self.node = node
        self.event = event_object


class TrackAutoPlayEvent(PyLavEvent):
    """This event is dispatched when the player starts to play a track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing
    """

    __slots__ = ("player", "track")

    def __init__(self, player: Player, track: Track) -> None:
        super().__init__()
        self.player = player
        self.track = track


class TrackResumedEvent(PyLavEvent):
    """This event is dispatched when the player resumes playing a track.

    Attributes
    ----------
    player: :class:`Player`
        The player that resumed playing a track.
    track: :class:`Track`
        The track that resumed playing.
    requester: :class:`discord.Member`
        The member that requested the track to resume playing.

    Parameters
    ----------
    player: :class:`Player`
        The player that resumed playing a track.
    track: :class:`Track`
        The track that resumed playing.
    requester: :class:`discord.Member`
        The member that requested the track to resume playing.
    """

    __slots__ = ("player", "track", "requester")

    def __init__(self, player: Player, track: Track, requester: discord.Member) -> None:
        super().__init__()
        self.player = player
        self.track = track
        self.requester = requester


class TrackSeekEvent(PyLavEvent):
    """This event is dispatched when the player is moved.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    track: :class:`Track`
        The track that was seeked.
    after: float
        The position in the track that was seeked to.
    before: float
        The position in the track that was seeked from.

    """

    __slots__ = ("player", "requester", "track", "before", "after")

    def __init__(self, player: Player, requester: discord.Member, track: Track, before: float, after: float) -> None:
        super().__init__()
        self.player = player
        self.requester = requester
        self.track = track
        self.before = before
        self.after = after


class TrackPreviousRequestedEvent(PyLavEvent):
    """This event is dispatched when a history track is requested.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    track: :class:`Track`
        The track that was seeked.
    """

    __slots__ = ("player", "requester", "track")

    def __init__(self, player: Player, requester: discord.Member, track: Track) -> None:
        super().__init__()
        self.player = player
        self.requester = requester
        self.track = track


class TracksRequestedEvent(PyLavEvent):
    """This event is dispatched when a track in added to the queue.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    tracks: :class:`list` of :class:`Track`
        The tracks that were added to the queue.
    """

    __slots__ = ("player", "requester", "tracks")

    def __init__(self, player: Player, requester: discord.Member, tracks: list[Track]) -> None:
        super().__init__()
        self.player = player
        self.requester = requester
        self.tracks = tracks


class TrackSkippedEvent(PyLavEvent):
    """This event is dispatched when a track is skipped.

    Attributes
    ----------
    player: :class:`Player`
        The player whose track was skipped.
    track: :class:`Track`
        The track that was skipped.
    requester: :class:`discord.Member`
        The user who requested the change.
    position: :class:`float`
        The position of the track before the skip.

    Parameters
    ----------
    player: :class:`Player`
        The player whose track was skipped.
    track: :class:`Track`
        The track that was skipped.
    requester: :class:`discord.Member`
        The user who requested the change.
    position: :class:`float`
        The position of the track before the skip.
    """

    __slots__ = ("player", "track", "requester", "position")

    def __init__(self, player: Player, requester: discord.Member, track: Track, position: float) -> None:
        super().__init__()
        self.player = player
        self.track = track
        self.requester = requester
        self.position = position
