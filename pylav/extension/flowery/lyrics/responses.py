from __future__ import annotations

from dataclasses import dataclass, field
from typing import NotRequired  # noqa


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class LyricsExternal:
    """External IDs for a track."""

    isrc: str
    spotify_id: str


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class LyricsMedia:
    """Media for a track."""

    preview: str | None
    artwork: str | None


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class LyricsTrack:
    """Track information for a track."""

    title: str
    artist: str
    album: str
    duration: int
    explicit: bool
    external: LyricsExternal | dict
    media: LyricsMedia | dict

    def __post_init__(self):
        if isinstance(self.media, dict):
            object.__setattr__(self, "media", LyricsMedia(**self.media))
        if isinstance(self.external, dict):
            object.__setattr__(self, "external", LyricsExternal(**self.external))


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class Task:
    """Task information for a query."""

    id: str
    status: str


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class LyricsLine:
    """The timed lyric detaild for a section."""

    text: str
    start: int
    duration: int


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class LyricsMetadata:
    """Lyrics metadata for a track."""

    text: str
    lines: list[LyricsLine]

    def __post_init__(self):
        temp = []
        for s in self.lines:
            if isinstance(s, LyricsLine) or (isinstance(s, dict) and (s := LyricsLine(**s))):
                temp.append(s)
        object.__setattr__(self, "lines", temp)


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class Lyrics:
    """Lyrics for a track."""

    track: LyricsTrack | dict
    task: Task | None | dict
    lyrics: LyricsMetadata | None | dict = None
    provider: NotRequired[str] = field(
        repr=False, compare=False, hash=False, default="Flowery API - https://flowery.pw"
    )

    def __post_init__(self):
        if isinstance(self.track, dict):
            object.__setattr__(self, "track", LyricsTrack(**self.track))
        if isinstance(self.task, dict):
            object.__setattr__(self, "task", Task(**self.task))
        if isinstance(self.lyrics, dict):
            object.__setattr__(self, "lyrics", LyricsMetadata(**self.lyrics))


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class Error:
    """Error information for a query."""

    error: str


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class TrackList:
    """Track list information for a query."""

    tracks: list[LyricsTrack]

    def __post_init__(self):
        temp = []
        for s in self.tracks:
            if isinstance(s, LyricsTrack) or (isinstance(s, dict) and (s := LyricsTrack(**s))):
                temp.append(s)
        object.__setattr__(self, "tracks", temp)
