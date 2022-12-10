from dataclasses import dataclass


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class LyricsExternal:
    isrc: str
    spotify_id: str


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class LyricsMedia:
    preview: str | None
    artwork: str


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class LyricsTrack:
    title: str
    artist: str
    album: str
    duration: int
    explicit: bool
    external: LyricsExternal
    media: LyricsMedia


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class Task:
    id: str
    status: str


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class LyricsLine:
    text: str
    start: int
    duration: int


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class LyricsMetadata:
    text: str
    lines: list[LyricsLine]


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class Lyrics:
    track: LyricsTrack
    task: Task | None
    lyrics: LyricsMetadata | None = None


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class Error:
    error: str


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class TrackList:
    tracks: list[LyricsTrack]
