from __future__ import annotations

from typing import TYPE_CHECKING

from pylav.events.base import PyLavEvent
from pylav.nodes.api.responses.websocket import TrackStart

if TYPE_CHECKING:
    from pylav.nodes.node import Node
    from pylav.players.player import Player
    from pylav.players.tracks.obj import Track


class TrackStartEvent(PyLavEvent):
    """This event is dispatched when the player starts to play a track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        self.player = player
        self.track = track
        self.node = node
        self.event = event_object


class TrackStartYouTubeEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a YouTube track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


# noinspection SpellCheckingInspection
class TrackStartClypitEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Clyp.it track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartGetYarnEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a GetYarn track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartMixCloudEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a MixCloud track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartOCRMixEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a OCR Mix track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartPornHubEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Pornhub track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartRedditEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Reddit track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


# noinspection SpellCheckingInspection
class TrackStartSoundgasmEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Soundgasm track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartTikTokEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a TikTok track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartSpotifyEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Spotify track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartDeezerEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Deezer track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartYandexMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Yandex Music track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartAppleMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play an Apple Music track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartBandcampEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Bandcamp track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartYouTubeMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a YouTube Music track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartSoundCloudEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a SoundCloud track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartTwitchEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Twitch track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartHTTPEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play an HTTP track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartLocalFileEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a local file track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartNicoNicoEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a NicoNico track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartVimeoEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Vimeo track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartSpeakEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Speak track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartGCTTSEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Google Cloud TTS track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
