from __future__ import annotations

import collections
from typing import TYPE_CHECKING, Literal

import discord

from pylav.events.base import PyLavEvent
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
    """This event is dispatched when the player's progress changes."""

    __slots__ = ()

    def __init__(self, player: Player, position: float, timestamp: float) -> None:
        self.player = player
        self.position = position
        self.timestamp = timestamp


class PlayerPausedEvent(PyLavEvent):
    """This event is dispatched when a player is paused."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.Member) -> None:
        self.player = player
        self.requester = requester


class PlayerStoppedEvent(PyLavEvent):
    """This event is dispatched when a player is stopped."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.Member) -> None:
        self.player = player
        self.requester = requester


class PlayerResumedEvent(PyLavEvent):
    """This event is dispatched when a player is resumed."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.Member) -> None:
        self.player = player
        self.requester = requester


class PlayerRestoredEvent(PyLavEvent):
    """This event is dispatched when a player is restored."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.abc.User) -> None:
        self.player = player
        self.requester = requester


class PlayerMovedEvent(PyLavEvent):
    """This event is dispatched when the player is moved."""

    __slots__ = ()

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
    """This event is dispatched when the player is disconnected."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.Member) -> None:
        self.player = player
        self.requester = requester
        self.current_track: Track | None = player.current
        self.position: float = player.estimated_position
        self.queue: collections.deque[Track] = player.queue.raw_queue


class PlayerConnectedEvent(PyLavEvent):
    """This event is dispatched when the player is connected."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.Member | None) -> None:
        self.player = player
        self.requester = requester


class PlayerVolumeChangedEvent(PyLavEvent):
    """This event is dispatched when the player has its volume changed."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.Member, before: int, after: int) -> None:
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after


class PlayerRepeatEvent(PyLavEvent):
    """This event is dispatched when the player repeat config changed."""

    __slots__ = ()

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
    """This event is dispatched when filters are applied."""

    __slots__ = ()

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
    """This event is dispatched when a track is played with higher priority than the current track."""

    __slots__ = ()

    def __init__(self, player: Player, requester: discord.Member, track: Track) -> None:
        self.player = player
        self.requester = requester
        self.track = track


class PlayerAutoDisconnectedEmptyQueueEvent(PyLavEvent):
    """This event is dispatched when the player is auto disconnected."""

    __slots__ = ()

    def __init__(self, player: Player) -> None:
        self.player = player
        self.requester = player.guild.me
        self.current_track: Track | None = player.current
        self.position: float = player.estimated_position
        self.queue: collections.deque[Track] = player.queue.raw_queue


class PlayerAutoDisconnectedAloneEvent(PyLavEvent):
    """This event is dispatched when the player is auto disconnected."""

    __slots__ = ()

    def __init__(self, player: Player) -> None:
        self.player = player
        self.requester = player.guild.me
        self.current_track: Track | None = player.current
        self.position: float = player.estimated_position
        self.queue: collections.deque[Track] = player.queue.raw_queue


class PlayerAutoPausedEvent(PyLavEvent):
    """This event is dispatched when the player is auto paused."""

    __slots__ = ()

    def __init__(self, player: Player) -> None:
        self.player = player
        self.requester = player.guild.me


class PlayerAutoResumedEvent(PyLavEvent):
    """This event is dispatched when the player is auto resumed."""

    __slots__ = ()

    def __init__(self, player: Player) -> None:
        self.player = player
        self.requester = player.guild.me
