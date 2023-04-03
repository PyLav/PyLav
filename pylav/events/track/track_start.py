from __future__ import annotations

from typing import TYPE_CHECKING

from pylav.events.base import PyLavEvent
from pylav.nodes.api.responses.websocket import TrackStart

if TYPE_CHECKING:
    from pylav.nodes.node import Node
    from pylav.players.player import Player
    from pylav.players.tracks.obj import Track


class TrackStartEvent(PyLavEvent):
    """This event is dispatched when the player starts to play a track.

    Event can be listened to by adding a listener with the name `pylav_track_start_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.
    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        self.player = player
        self.track = track
        self.node = node
        self.event = event_object


class TrackStartYouTubeEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a YouTube track.

    Event can be listened to by adding a listener with the name `pylav_track_start_youtube_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


# noinspection SpellCheckingInspection
class TrackStartClypitEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Clyp.it track.

    Event can be listened to by adding a listener with the name `pylav_track_start_clypit_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartGetYarnEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a GetYarn track.

    Event can be listened to by adding a listener with the name `pylav_track_start_get_yarn_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartMixCloudEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a MixCloud track.

    Event can be listened to by adding a listener with the name `pylav_track_start_mix_cloud_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartOCRMixEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a OCR Mix track.

    Event can be listened to by adding a listener with the name `pylav_track_start_ocr_mix_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartPornHubEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Pornhub track.

    Event can be listened to by adding a listener with the name `pylav_track_start_porn_hub_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartRedditEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Reddit track.

    Event can be listened to by adding a listener with the name `pylav_track_start_reddit_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


# noinspection SpellCheckingInspection
class TrackStartSoundgasmEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Soundgasm track.

    Event can be listened to by adding a listener with the name `pylav_track_start_soundgasm_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartTikTokEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a TikTok track.

    Event can be listened to by adding a listener with the name `pylav_track_start_tik_tok_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartSpotifyEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Spotify track.

    Event can be listened to by adding a listener with the name `pylav_track_start_spotify_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartDeezerEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Deezer track.

    Event can be listened to by adding a listener with the name `pylav_track_start_deezer_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartYandexMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Yandex Music track.

    Event can be listened to by adding a listener with the name `pylav_track_start_yandex_music_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartAppleMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play an Apple Music track.

    Event can be listened to by adding a listener with the name `pylav_track_start_apple_music_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartBandcampEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Bandcamp track.

    Event can be listened to by adding a listener with the name `pylav_track_start_bandcamp_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartYouTubeMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a YouTube Music track.

    Event can be listened to by adding a listener with the name `pylav_track_start_youtube_music_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartSoundCloudEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a SoundCloud track.

    Event can be listened to by adding a listener with the name `pylav_track_start_soundcloud_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartTwitchEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Twitch track.

    Event can be listened to by adding a listener with the name `pylav_track_start_twitch_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartHTTPEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play an HTTP track.

    Event can be listened to by adding a listener with the name `pylav_track_start_http_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartLocalFileEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a local file track.

    Event can be listened to by adding a listener with the name `pylav_track_start_local_file_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartNicoNicoEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a NicoNico track.

    Event can be listened to by adding a listener with the name `pylav_track_start_nico_nico_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartVimeoEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Vimeo track.

    Event can be listened to by adding a listener with the name `pylav_track_start_vimeo_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartSpeakEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Speak track.

    Event can be listened to by adding a listener with the name `pylav_track_start_speak_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)


class TrackStartGCTTSEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Google Cloud TTS track.

    Event can be listened to by adding a listener with the name `pylav_track_start_gctts_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that started to play the track.
    track: :class:`Track`
        The track that was started.
    node: :class:`Node`
        The node that dispatched the event.
    event: :class:`TrackStart`
        The raw event object.

    """

    __slots__ = ("player", "track", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
        super().__init__(player, track, node, event_object)
