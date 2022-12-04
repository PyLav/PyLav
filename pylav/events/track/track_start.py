from __future__ import annotations

from pylav.events.base import PyLavEvent
from pylav.nodes.api.responses.websocket import TrackStart
from pylav.players.tracks.obj import Track


class TrackStartEvent(PyLavEvent):
    """This event is dispatched when the player starts to play a track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        self.player = player
        self.track = track
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author
        self.node = node
        self.event = event_object


class TrackStartYouTubeEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a YouTube track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartClypitEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Clyp.it track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartGetYarnEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a GetYarn track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartMixCloudEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a MixCloud track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartOCRMixEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a OCR Mix track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartPornHubEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Pornhub track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartRedditEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Reddit track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartSoundgasmEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Soundgasm track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartTikTokEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a TikTok track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartSpotifyEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Spotify track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartDeezerEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Deezer track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartYandexMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Yandex Music track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartAppleMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play an Apple Music track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartBandcampEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Bandcamp track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartYouTubeMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a YouTube Music track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartSoundCloudEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a SoundCloud track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartTwitchEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Twitch track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartHTTPEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play an HTTP track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartLocalFileEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a local file track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartNicoNicoEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a NicoNico track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartVimeoEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Vimeo track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartSpeakEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Speak track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartGCTTSEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Google Cloud TTS track."""

    __slots__ = ()

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author
