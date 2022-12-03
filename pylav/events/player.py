import collections
from typing import Literal

import discord

from pylav.events.base import PyLavEvent
from pylav.players.tracks.obj import Track


class PlayerUpdateEvent(PyLavEvent):
    """This event is dispatched when the player's progress changes.

    Attributes
    ----------
    player: :class:`Player`
        The player that's progress was updated.
    position: :class:`int`
        The position of the player that was changed to.
    timestamp: :class:`int`
        The timestamp that the player is currently on.

    Parameters
    ----------
    player: :class:`Player`
        The player that's progress was updated.
    position: :class:`float`
        The position of the player that was changed to.
    timestamp: :class:`float`
        The timestamp that the player is currently on.
    """

    __slots__ = ("player", "position", "timestamp")

    def __init__(self, player: Player, position: float, timestamp: float) -> None:
        super().__init__()
        self.player = player
        self.position = position
        self.timestamp = timestamp


class PlayerPausedEvent(PyLavEvent):
    """This event is dispatched when a player is paused.

    Attributes
    ----------
    player: :class:`Player`
        The player whose track was paused.
    requester: :class:`discord.Member`
        The user who requested the change.

    Parameters
    ----------
    player: :class:`Player`
        The player whose track was paused.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member) -> None:
        super().__init__()
        self.player = player
        self.requester = requester


class PlayerStoppedEvent(PyLavEvent):
    """This event is dispatched when a player is stopped.

    Attributes
    ----------
    player: :class:`Player`
        The player which was stopped.
    requester: :class:`discord.Member`
        The user who requested the change.

    Parameters
    ----------
    player: :class:`Player`
        The player which was stopped.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member) -> None:
        super().__init__()
        self.player = player
        self.requester = requester


class PlayerResumedEvent(PyLavEvent):
    """This event is dispatched when a player is resumed.

    Attributes
    ----------
    player: :class:`Player`
        The player whose track was resumed.
    requester: :class:`discord.Member`
        The user who requested the change.

    Parameters
    ----------
    player: :class:`Player`
        The player whose track was resumed.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member) -> None:
        super().__init__()
        self.player = player
        self.requester = requester


class PlayerRestoredEvent(PyLavEvent):
    """This event is dispatched when a player is restored.

    Attributes
    ----------
    player: :class:`Player`
        The player whose track was restored.
    requester: :class:`discord.Member`
        The user who requested the change.

    Parameters
    ----------
    player: :class:`Player`
        The player whose track was restored.
    requester: :class:`discord.abc.User`
        The user who requested the change.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.abc.User) -> None:
        super().__init__()
        self.player = player
        self.requester = requester


class PlayerMovedEvent(PyLavEvent):
    """This event is dispatched when the player is moved.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    before: :class:`discord.channel.VocalGuildChannel`
        The channel the player was in before the move.
    after: :class:`discord.channel.VocalGuildChannel`
        The channel the player is in now.
    """

    __slots__ = ("player", "requester", "before", "after")

    def __init__(
        self,
        player: Player,
        requester: discord.Member,
        before: discord.channel.VocalGuildChannel,
        after: discord.channel.VocalGuildChannel,
    ) -> None:
        super().__init__()
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after


class PlayerDisconnectedEvent(PyLavEvent):
    """This event is dispatched when the player is moved.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    current_track: :class:`Track`
        The track that was playing when the player disconnected.
    position: :class:`int`
        The position of the track that was playing when the player disconnected.
    queue: :class:`collections.deque` of :class:`Track`
        The tracks that are in the queue when the player disconnected.

    Parameters
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "requester", "current_track", "position", "queue")

    def __init__(self, player: Player, requester: discord.Member) -> None:
        super().__init__()
        self.player = player
        self.requester = requester
        self.current_track: Track | None = player.current
        self.position: float = player.position
        self.queue: collections.deque[Track] = player.queue.raw_queue


class PlayerConnectedEvent(PyLavEvent):
    """This event is dispatched when the player is moved.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member | None) -> None:
        super().__init__()
        self.player = player
        self.requester = requester


class PlayerVolumeChangedEvent(PyLavEvent):
    """This event is dispatched when the player is moved.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    before: float
        The volume before the change.
    after: float
        The volume after the change.

    """

    __slots__ = ("player", "requester", "before", "after")

    def __init__(self, player: Player, requester: discord.Member, before: int, after: int) -> None:
        super().__init__()
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after


class PlayerRepeatEvent(PyLavEvent):
    """This event is dispatched when the player is moved.

    Attributes
    ----------
    player: :class:`Player`
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
    ) -> None:
        super().__init__()
        self.player = player
        self.requester = requester
        self.queue_before = queue_before
        self.queue_after = queue_after
        self.current_before = current_before
        self.current_after = current_after
        self.type = op_type


class SegmentSkippedEvent(PyLavEvent):
    """This event is dispatched when a segment is skipped.

    Attributes
    ----------
    player: :class:`Player`
        The player whose segment was skipped.
    segment: :class:`SegmentObject`
        The segment that was skipped.
    node: :class:`Node`
        The node the player was in.

    Parameters
    ----------
    player: :class:`Player`
        The player whose segment was skipped.
    node: :class:`Node`
        The node the player was in.
    """

    __slots__ = ("player", "segment", "node", "event")

    def __init__(self, player: Player, node: Node, event_object: SegmentSkippedEventOpObject) -> None:
        self.player = player
        self.segment = event_object.segment
        self.node = node
        self.event = event_object


class SegmentsLoadedEvent(PyLavEvent):
    """This event is dispatched when segments are loaded.

    Attributes
    ----------
    player: :class:`Player`
        The player whose segments were loaded.
    segments: :class:`list` of :class:`SegmentObject`
        The segments that were loaded.
    node: :class:`Node`
        The node the player was in.

    Parameters
    ----------
    player: :class:`Player`
        The player whose segments were loaded.
    node: :class:`Node`
        The node the player was in.
    event_object: :class:`SegmentsLoadedEventOpObject`
        The event object that was received from Lavalink.
    """

    __slots__ = ("player", "segments", "node", "event")

    def __init__(self, player: Player, node: Node, event_object: SegmentsLoadedEventObject) -> None:
        self.player = player
        self.segments = event_object.segments
        self.node = node
        self.event = event_object


class FiltersAppliedEvent(PyLavEvent):
    """This event is dispatched when filters are applied.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    volume: :class:`Volume`
        The volume that was set.
    equalizer: :class:`Equalizer`
        The equalizer that was set.
    karaoke: :class:`Karaoke`
        The karaoke that was set.
    timescale: :class:`Timescale`
        The timescale that was set.
    tremolo: :class:`Tremolo`
        The tremolo that was set.
    vibrato: :class:`Vibrato`
        The vibrato that was set.
    rotation: :class:`Rotation`
        The rotation that was set.
    distortion: :class:`Distortion`
        The distortion that was set.
    echo : :class:`Echo`
        The echo filter that was set
    low_pass: :class:`Lowpass`
        The lowpass that was set.
    channel_mix: :class:`ChannelMix`
        The channel mix that was set.
    node: :class:`Node`
        The node that was changed.

    Parameters
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    volume: :class:`Volume`
        The volume that was set.
    equalizer: :class:`Equalizer`
        The equalizer that was set.
    karaoke: :class:`Karaoke`
        The karaoke that was set.
    timescale: :class:`Timescale`
        The timescale that was set.
    tremolo: :class:`Tremolo`
        The tremolo that was set.
    vibrato: :class:`Vibrato`
        The vibrato that was set.
    rotation: :class:`Rotation`
        The rotation that was set.
    distortion: :class:`Distortion`
        The distortion that was set.
    low_pass: :class:`Lowpass`
        The lowpass that was set.
    channel_mix: :class:`ChannelMix`
        The channel mix that was set.
    echo: :class:`Echo`
        The echo filter that was set
    node: :class:`Node`
        The node that was changed.
    """

    __slots__ = (
        "player",
        "requester",
        "volume",
        "equalizer",
        "karaoke",
        "timescale",
        "tremolo",
        "vibrato",
        "rotation",
        "distortion",
        "echo",
        "low_pass",
        "channel_mix",
        "node",
    )

    def __init__(
        self,
        player: Player,
        requester: discord.Member,
        node: Node,
        volume: Volume | None = None,
        equalizer: Equalizer | None = None,
        karaoke: Karaoke | None = None,
        timescale: Timescale | None = None,
        tremolo: Tremolo | None = None,
        vibrato: Vibrato | None = None,
        rotation: Rotation | None = None,
        distortion: Distortion | None = None,
        low_pass: LowPass | None = None,
        channel_mix: ChannelMix | None = None,
        echo: Echo | None = None,
    ) -> None:
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
        self.node = node
        self.echo = echo


class QuickPlayEvent(PyLavEvent):
    """This event is dispatched when a track is played with higher priority than the current track.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    track: :class:`Track`
        The track that was played.
    """

    __slots__ = ("player", "requester", "track")

    def __init__(self, player: Player, requester: discord.Member, track: Track) -> None:
        self.player = player
        self.requester = requester
        self.track = track
