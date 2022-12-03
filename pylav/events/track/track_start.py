from pylav.events.base import PyLavEvent


class TrackStartEvent(PyLavEvent):
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
    event_object: TrackStartEventOpObject:
        The event object that was sent from the websocket.
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node", "event")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__()
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartDeezerEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Deezer track.

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
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartYandexMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Yandex Music track.

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
    """

    __slots__ = ("player", "track", "url", "identifier", "duration", "title", "author", "node")

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartAppleMusicEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play an Apple Music track.

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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartHTTPEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play an HTTP track.

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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author


class TrackStartSpeakEvent(TrackStartEvent):
    """This event is dispatched when the player starts to play a Speak track.

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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
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

    def __init__(self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject) -> None:
        super().__init__(player, track, node, event_object)
        self.url = track.uri
        self.identifier = track.identifier
        self.duration = track.duration
        self.title = track.title
        self.author = track.author
