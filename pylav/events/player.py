from __future__ import annotations

import collections
from typing import TYPE_CHECKING, Literal

import discord
from dacite import from_dict

from pylav.events.base import PyLavEvent
from pylav.events.utils import PluginInfoTypeHint
from pylav.nodes.node import Node

if TYPE_CHECKING:
    from pylav.players.filters import (
        ChannelMix,
        Distortion,
        Echo,
        Equalizer,
        Karaoke,
        LowPass,
        Rotation,
        Timescale,
        Tremolo,
        Vibrato,
        Volume,
    )
    from pylav.players.player import Player
    from pylav.players.tracks.obj import Track


class PlayerUpdateEvent(PyLavEvent):
    """This event is dispatched when the player's progress changes.

    Event can be listened to by adding a listener with the name `pylav_player_update_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that was updated.
    position: :class:`float`
        The position of the player.
    timestamp: :class:`float`
        The timestamp of the event.
    """

    __slots__ = ("player", "position", "timestamp")

    def __init__(self, player: Player, position: float, timestamp: float) -> None:
        self.player = player
        self.position = position
        self.timestamp = timestamp


class PlayerPausedEvent(PyLavEvent):
    """This event is dispatched when a player is paused.

    Event can be listened to by adding a listener with the name `pylav_player_paused_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that was paused.
    requester: :class:`discord.Member`
        The member that requested the pause.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member) -> None:
        self.player = player
        self.requester = requester


class PlayerStoppedEvent(PyLavEvent):
    """This event is dispatched when a player is stopped.

    Event can be listened to by adding a listener with the name `pylav_player_stopped_event`.


    Attributes
    ----------
    player: :class:`Player`
        The player that was stopped.
    requester: :class:`discord.Member`
        The member that requested the stop.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member) -> None:
        self.player = player
        self.requester = requester


class PlayerResumedEvent(PyLavEvent):
    """This event is dispatched when a player is resumed.

    Event can be listened to by adding a listener with the name `pylav_player_resumed_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that was resumed.
    requester: :class:`discord.Member`
        The member that requested the resume.

    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member) -> None:
        self.player = player
        self.requester = requester


class PlayerRestoredEvent(PyLavEvent):
    """This event is dispatched when a player is restored.

    Event can be listened to by adding a listener with the name `pylav_player_restored_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that was restored.
    requester: :class:`discord.Member`
        The member that requested the restore.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.abc.User) -> None:
        self.player = player
        self.requester = requester


class PlayerMovedEvent(PyLavEvent):
    """This event is dispatched when the player is moved.

    Event can be listened to by adding a listener with the name `pylav_player_moved_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that was moved.
    requester: :class:`discord.Member`
        The member that requested the move.
    before: :class:`discord.channel.VocalGuildChannel`
        The channel the player was in before the move.
    after: :class:`discord.channel.VocalGuildChannel`
        The channel the player is in after the move.
    """

    __slots__ = ("player", "requester", "before", "after")

    def __init__(
        self,
        player: Player,
        requester: discord.Member,
        before: discord.channel.VocalGuildChannel,
        after: discord.channel.VocalGuildChannel,
    ) -> None:
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after


class PlayerDisconnectedEvent(PyLavEvent):
    """This event is dispatched when the player is disconnected.

    Event can be listened to by adding a listener with the name `pylav_player_disconnected_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that was disconnected.
    requester: :class:`discord.Member`
        The member that requested the disconnect.
    current_track: :class:`Track` | :class:`None`
        The current track that was playing when the player was disconnected.
    position: :class:`float`
        The position of the current track when the player was disconnected.
    queue: :class:`collections.deque[Track]`
        The queue of the player when the player was disconnected.
    """

    __slots__ = ("player", "requester", "current_track", "position", "queue")

    def __init__(self, player: Player, requester: discord.Member) -> None:
        self.player = player
        self.requester = requester
        self.current_track: Track | None = player.current
        self.position: float = player.estimated_position
        self.queue: collections.deque[Track] = player.queue.raw_queue


class PlayerConnectedEvent(PyLavEvent):
    """This event is dispatched when the player is connected.

    Event can be listened to by adding a listener with the name `pylav_player_connected_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that was connected.
    requester: :class:`discord.Member` | :class:`None`
        The member that requested the connect.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member | None) -> None:
        self.player = player
        self.requester = requester


class PlayerVolumeChangedEvent(PyLavEvent):
    """This event is dispatched when the player has its volume changed.

    Event can be listened to by adding a listener with the name `pylav_player_volume_changed_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that had its volume changed.
    requester: :class:`discord.Member`
        The member that requested the volume change.
    before: :class:`float`
        The volume before the change.
    after: :class:`float`
        The volume after the change.
    """

    __slots__ = ("player", "requester", "before", "after")

    def __init__(self, player: Player, requester: discord.Member, before: int, after: int) -> None:
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after


class PlayerRepeatEvent(PyLavEvent):
    """This event is dispatched when the player repeat config changed.

    Event can be listened to by adding a listener with the name `pylav_player_repeat_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that had its repeat config changed.
    requester: :class:`discord.Member`
        The member that requested the repeat change.
    type: :class:`str`
        The type of operation that was performed, "current" or "queue"
    queue_before: :class:`bool`
        The queue repeat state before the operation.
    queue_after: :class:`bool`
        The queue repeat state after the operation.
    current_before: :class:`bool`
        The current track repeat state before the operation.
    current_after: :class:`bool`
        The current track repeat state after the operation.
    """

    __slots__ = ("player", "requester", "type", "queue_before", "queue_after", "current_before", "current_after")

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
        self.player = player
        self.requester = requester
        self.queue_before = queue_before
        self.queue_after = queue_after
        self.current_before = current_before
        self.current_after = current_after
        self.type = op_type


class FiltersAppliedEvent(PyLavEvent):
    """This event is dispatched when filters are applied.

    Event can be listened to by adding a listener with the name `filters_applied_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that had filters applied.
    requester: :class:`discord.Member`
        The member that requested the filters to be applied.
    volume: :class:`Volume` | :class:`None`
        The volume filter.
    equalizer: :class:`Equalizer` | :class:`None`
        The equalizer filter.
    karaoke: :class:`Karaoke` | :class:`None`
        The karaoke filter.
    timescale: :class:`Timescale` | :class:`None`
        The timescale filter.
    tremolo: :class:`Tremolo` | :class:`None`
        The tremolo filter.
    vibrato: :class:`Vibrato` | :class:`None`
        The vibrato filter.
    rotation: :class:`Rotation` | :class:`None`
        The rotation filter.
    distortion: :class:`Distortion` | :class:`None`
        The distortion filter.
    low_pass: :class:`LowPass` | :class:`None`
        The low pass filter.
    channel_mix: :class:`ChannelMix` | :class:`None`
        The channel mix filter.
    echo: :class:`Echo` | :class:`None`
        The echo filter.
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
        "low_pass",
        "channel_mix",
        "echo",
        "pluginFilters",
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
        pluginFilters: dict[str, Echo | None] = None,
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

        self.pluginFilters = from_dict(data=pluginFilters, data_class=PluginInfoTypeHint) if pluginFilters else None
        self.echo = echo if echo else self.pluginFilters.echo if self.pluginFilters else None


class QuickPlayEvent(PyLavEvent):
    """This event is dispatched when a track is played with higher priority than the current track.

    Event can be listened to by adding a listener with the name `quick_play_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that had a track played.
    requester: :class:`discord.Member`
        The member that requested the track to be played.
    track: :class:`Track`
        The track that was played.
    """

    __slots__ = ("player", "requester", "track")

    def __init__(self, player: Player, requester: discord.Member, track: Track) -> None:
        self.player = player
        self.requester = requester
        self.track = track


class PlayerAutoDisconnectedEmptyQueueEvent(PyLavEvent):
    """This event is dispatched when the player is auto disconnected due to an empty queue.

    Event can be listened to by adding a listener with the name `player_auto_disconnected_empty_queue_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that was auto disconnected.
    requester: :class:`discord.Member`
        The member that requested the player to be auto disconnected.
    current_track: :class:`Track` | :class:`None`
        The current track that was playing.
    position: :class:`float`
        The position of the current track.
    queue: :class:`collections.deque[Track]`
        The queue of the player when it was auto disconnected.

    """

    __slots__ = ("player", "requester", "current_track", "position", "queue")

    def __init__(self, player: Player) -> None:
        self.player = player
        self.requester = player.guild.me
        self.current_track: Track | None = player.current
        self.position: float = player.estimated_position
        self.queue: collections.deque[Track] = player.queue.raw_queue


class PlayerAutoDisconnectedAloneEvent(PyLavEvent):
    """This event is dispatched when the player is auto disconnected due to it being alone in the voice channel.

    Event can be listened to by adding a listener with the name `player_auto_disconnected_alone_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that was auto disconnected.
    requester: :class:`discord.Member`
        The member that requested the player to be auto disconnected.
    current_track: :class:`Track` | :class:`None`
        The current track that was playing.
    position: :class:`float`
        The position of the current track.
    queue: :class:`collections.deque[Track]`
        The queue of the player when it was auto disconnected.
    """

    __slots__ = ("player", "requester", "current_track", "position", "queue")

    def __init__(self, player: Player) -> None:
        self.player = player
        self.requester = player.guild.me
        self.current_track: Track | None = player.current
        self.position: float = player.estimated_position
        self.queue: collections.deque[Track] = player.queue.raw_queue


class PlayerAutoPausedEvent(PyLavEvent):
    """This event is dispatched when the player is auto paused.

    Event can be listened to by adding a listener with the name `player_auto_paused_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that was auto paused.
    requester: :class:`discord.Member`
        The member that requested the player to be auto paused.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player) -> None:
        self.player = player
        self.requester = player.guild.me


class PlayerAutoResumedEvent(PyLavEvent):
    """This event is dispatched when the player is auto resumed.

    Event can be listened to by adding a listener with the name `player_auto_resumed_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that was auto resumed.
    requester: :class:`discord.Member`
        The member that requested the player to be auto resumed.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player) -> None:
        self.player = player
        self.requester = player.guild.me
