from __future__ import annotations

import collections
from typing import TYPE_CHECKING, Literal

import discord

from pylav.filters import (
    ChannelMix,
    Distortion,
    Echo,
    Equalizer,
    Karaoke,
    LowPass,
    Rotation,
    Timescale,
    Vibrato,
    Volume,
)
from pylav.filters.tremolo import Tremolo
from pylav.utils import Segment

if TYPE_CHECKING:
    from pylav.node import Node
    from pylav.player import Player
    from pylav.tracks import Track


class Event:
    """The base for all Lavalink events"""


class QueueEndEvent(Event):
    """This event is dispatched when there are no more songs in the queue.

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

    def __init__(self, player: Player):
        self.player = player


class TrackStuckEvent(Event):
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
    threshold: :class:`float`
        The amount of time the track had while being stuck.
    node: :class:`Node`
        The node that the stuck track is playing on.
    """

    __slots__ = ("player", "track", "threshold", "node")

    def __init__(self, player: Player, track: Track, threshold: float, node: Node):
        self.player = player
        self.track = track
        self.threshold = threshold
        self.node = node


class TrackExceptionEvent(Event):
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
    exception: :class:`Exception`
        The type of exception that the track had while playing.
    node: :class:`Node`
        The node that the exception occurred on.
    """

    __slots__ = ("player", "track", "exception", "node")

    def __init__(self, player: Player, track: Track, exception: Exception, node: Node):
        self.player = player
        self.track = track
        self.exception = exception
        self.node = node


class TrackEndEvent(Event):
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
    reason: :class:`str`
        The reason why the track stopped playing.
    node: :class:`Node`
        The node that the track finished playing on.
    """

    __slots__ = ("player", "track", "reason", "node")

    def __init__(self, player: Player, track: Track, reason: str, node: Node):
        self.player = player
        self.track = track
        self.reason = reason
        self.node = node


class TrackStartEvent(Event):
    """This event is dispatched when the player starts to play a track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        self.player = player
        self.track = track
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author
        self.node = node


class TrackAutoPlayEvent(Event):
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

    def __init__(self, player: Player, track: Track):
        self.player = player
        self.track = track


class TrackResumedEvent(Event):
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

    def __init__(self, player: Player, track: Track, requester: discord.Member):
        self.player = player
        self.track = track
        self.requester = requester


class TrackStartYouTubeEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a YouTube track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartClypitEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Clyp.it track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartGetYarnEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a GetYarn track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartMixCloudEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a MixCloud track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartOCRMixEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a OCR Mix track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartPornHubEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Pornhub track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartRedditEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Reddit track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartSoundgasmEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Soundgasm track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartTikTokEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a TikTok track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartSpotifyEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Spotify track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartAppleMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Apple Music track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartBandcampEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Bandcamp track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartYouTubeMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a YouTube Music track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartSoundCloudEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a SoundCloud track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartTwitchEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Twitch track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartHTTPEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a HTTP track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartLocalFileEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a local file track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartNicoNicoEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a NicoNico track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartVimeoEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Vimeo track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartSpeakEvent(TrackStartEvent):
    """This event is dispatched when t he player starts to play a Speak track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartGCTTSEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Google Cloud TTS track.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    url: :class:`str`
        The url of the track that started playing.
    identifier: :class:`str`
        The identifier of the track that started playing.
    duration: :class:`int`
        The duration of the track that started playing.
    title: :class:`str`
        The title of the track that started playing.
    author: :class:`str`
        The author of the track that started playing.
    node: :class:`Node`
        The node that the track started playing on.

    Parameters
    ----------
    player: :class:`Player`
        The player that started to play a track.
    track: :class:`Track`
        The track that started playing.
    node: :class:`Node`
        The node that the track started playing on.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node):
        super().__init__(player, track, node)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class PlayerUpdateEvent(Event):
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

    def __init__(self, player: Player, position: float, timestamp: float):
        self.player = player
        self.position = position
        self.timestamp = timestamp


class NodeDisconnectedEvent(Event):
    """This event is dispatched when a node disconnects and becomes unavailable.

    Attributes
    ----------
    node: :class:`Node`
        The node that was disconnected from.
    code: :class:`int`
        The status code of the event.
    reason: :class:`str`
        The reason of why the node was disconnected.

    Parameters
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
    """This event is dispatched when Lavalink.py successfully connects to a node.

    Attributes
    ----------
    node: :class:`Node`
        The node that was successfully connected to.

    Parameters
    ----------
    node: :class:`Node`
        The node that was successfully connected to.
    """

    __slots__ = ("node",)

    def __init__(self, node: Node):
        self.node = node


class NodeChangedEvent(Event):
    """This event is dispatched when a player changes to another node.
    Keep in mind this event can be dispatched multiple times if a node
    disconnects and the load balancer moves players to a new node.


    Attributes
    ----------
    player: :class:`Player`
        The player whose node was changed.
    old_node: :class:`Node`
        The node the player was moved from.
    new_node: :class:`Node`
        The node the player was moved to.

    Parameters
    ----------
    player: :class:`Player`
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
    """This event is dispatched when an audio websocket to Discord
    is closed. This can happen for various reasons like an
    expired voice server update.

    Attributes
    ----------
    player: :class:`Player`
        The player whose audio websocket was closed.
    code: :class:`int`
        The node the player was moved from.
    reason: :class:`str`
        The node the player was moved to.
    by_remote: :class:`bool`
        If the websocket was closed remotely.
    channel: :class:`discord.channel.VocalGuildChannel`
        The voice channel the player was in.
    node: :class:`Node`
        The node the player was in.

    Parameters
    ----------
    player: :class:`Player`
        The player whose audio websocket was closed.
    code: :class:`int`
        The node the player was moved from.
    reason: :class:`str`
        The node the player was moved to.
    by_remote: :class:`bool`
        If the websocket was closed remotely.
    channel: :class:`discord.channel.VocalGuildChannel`
        The voice channel the player was in.
    node: :class:`Node`
        The node the player was in.
    """

    __slots__ = ("player", "code", "reason", "by_remote", "node", "channel")

    def __init__(
        self,
        player: Player,
        code: int,
        reason: str,
        by_remote: bool,
        node: Node,
        channel: discord.channel.VocalGuildChannel,
    ):
        self.player = player
        self.code = code
        self.reason = reason
        self.by_remote = by_remote
        self.node = node
        self.channel = channel


class SegmentSkippedEvent(Event):
    """This event is dispatched when a segment is skipped.

    Attributes
    ----------
    player: :class:`Player`
        The player whose segment was skipped.
    segment: :class:`Segment`
        The segment that was skipped.
    node: :class:`Node`
        The node the player was in.

    Parameters
    ----------
    player: :class:`Player`
        The player whose segment was skipped.
    segment: :class:`Segment`
        The segment that was skipped.
    node: :class:`Node`
        The node the player was in.
    """

    __slots__ = ("player", "segment", "node")

    def __init__(self, player: Player, category: str, start: float, end: float, node: Node):
        self.player = player
        self.segment = Segment(category=category, start=start, end=end)
        self.node = node


class SegmentsLoadedEvent(Event):
    """This event is dispatched when segments are loaded.

    Attributes
    ----------
    player: :class:`Player`
        The player whose segments were loaded.
    segments: :class:`list` of :class:`Segment`
        The segments that were loaded.
    node: :class:`Node`
        The node the player was in.

    Parameters
    ----------
    player: :class:`Player`
        The player whose segments were loaded.
    segments: :class:`list` of :class:`Segment`
        The segments that were loaded.
    node: :class:`Node`
        The node the player was in.
    """

    __slots__ = ("player", "segments", "node")

    def __init__(self, player: Player, segments: list[dict], node: Node):
        self.player = player
        self.segments = [Segment(**segment) for segment in segments]
        self.node = node


class PlayerPausedEvent(Event):
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

    def __init__(self, player: Player, requester: discord.Member):
        self.player = player
        self.requester = requester


class PlayerStoppedEvent(Event):
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

    def __init__(self, player: Player, requester: discord.Member):
        self.player = player
        self.requester = requester


class PlayerResumedEvent(Event):
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

    def __init__(self, player: Player, requester: discord.Member):
        self.player = player
        self.requester = requester


class PlayerRestoredEvent(Event):
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

    def __init__(self, player: Player, requester: discord.abc.User):
        self.player = player
        self.requester = requester


class QueueTrackPositionChangedEvent(Event):
    """This event is dispatched when the position of a track is changed.

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

    def __init__(self, player: Player, before: int, after: int, requester: discord.Member, track: Track):
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after
        self.track = track


class TrackSkippedEvent(Event):
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

    def __init__(self, player: Player, requester: discord.Member, track: Track, position: float):
        self.player = player
        self.track = track
        self.requester = requester
        self.position = position


class QueueShuffledEvent(Event):
    """This event is dispatched when the queue is shuffled.

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

    def __init__(self, player: Player, requester: discord.Member):
        self.player = player
        self.requester = requester


class QueueTracksRemovedEvent(Event):
    """This event is dispatched when tracks are removed from the queue.

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

    def __init__(self, player: Player, requester: discord.Member, tracks: list[Track]):
        self.player = player
        self.requester = requester
        self.tracks = tracks


class FiltersAppliedEvent(Event):
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
        echo: Echo = None,
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
        self.node = node
        self.echo = echo


class PlayerMovedEvent(Event):
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
    ):
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after


class PlayerDisconnectedEvent(Event):
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

    def __init__(self, player: Player, requester: discord.Member):
        self.player = player
        self.requester = requester
        self.current_track: Track | None = player.current
        self.position: float = player.position
        self.queue: collections.deque = player.queue.raw_queue


class PlayerConnectedEvent(Event):
    """This event is dispatched when the player is moved.

    Attributes
    ----------
    player: :class:`Player`
        The player whose queue was shuffled.
    requester: :class:`discord.Member`
        The user who requested the change.
    """

    __slots__ = ("player", "requester")

    def __init__(self, player: Player, requester: discord.Member | None):
        self.player = player
        self.requester = requester


class TrackSeekEvent(Event):
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

    def __init__(self, player: Player, requester: discord.Member, track: Track, before: float, after: float):
        self.player = player
        self.requester = requester
        self.track = track
        self.before = before
        self.after = after


class PlayerVolumeChangedEvent(Event):
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

    def __init__(self, player: Player, requester: discord.Member, before: int, after: int):
        self.player = player
        self.requester = requester
        self.before = before
        self.after = after


class PlayerRepeatEvent(Event):
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
    ):
        self.player = player
        self.requester = requester
        self.queue_before = queue_before
        self.queue_after = queue_after
        self.current_before = current_before
        self.current_after = current_after
        self.type = op_type


class TrackPreviousRequestedEvent(Event):
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

    def __init__(self, player: Player, requester: discord.Member, track: Track):
        self.player = player
        self.requester = requester
        self.track = track


class TracksRequestedEvent(Event):
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

    def __init__(self, player: Player, requester: discord.Member, tracks: list[Track]):
        self.player = player
        self.requester = requester
        self.tracks = tracks


class QuickPlayEvent(Event):
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

    def __init__(self, player: Player, requester: discord.Member, track: Track):
        self.player = player
        self.requester = requester
        self.track = track
