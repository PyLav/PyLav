from __future__ import annotations

import dataclasses
from typing import NotRequired  # noqa

from piccolo.columns import Column

from pylav.constants.node import TRACK_VERSION
from pylav.nodes.api.responses.shared import TrackPluginInfo
from pylav.storage.database.tables.tracks import TrackRow
from pylav.type_hints.dict_typing import JSON_DICT_TYPE


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Info:
    identifier: str
    isSeekable: bool
    author: str
    length: int
    isStream: bool
    position: int
    title: str
    uri: str | None
    sourceName: str | None
    artworkUrl: str | None = None
    isrc: str | None = None
    version: NotRequired[int] = TRACK_VERSION

    def to_dict(self) -> JSON_DICT_TYPE:
        return dataclasses.asdict(self)

    def to_database(self) -> dict[Column, str | None]:
        # noinspection SpellCheckingInspection
        return {
            TrackRow.identifier: self.identifier,
            TrackRow.title: self.title,
            TrackRow.uri: self.uri,
            TrackRow.sourceName: self.sourceName,
            TrackRow.isrc: self.isrc,
            TrackRow.artworkUrl: self.artworkUrl,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Track:
    info: Info
    encoded: str = None
    pluginInfo: TrackPluginInfo | None = None

    def __post_init__(self) -> None:
        if self.pluginInfo is None:
            object.__setattr__(self, "pluginInfo", TrackPluginInfo(kwargs=None))

    def set_version(self, version: int) -> None:
        object.__setattr__(self.info, "version", version)

    def to_dict(self) -> JSON_DICT_TYPE:
        return {
            "info": dataclasses.asdict(self.info),
            "encoded": self.encoded,
            "pluginInfo": dataclasses.asdict(self.pluginInfo) if self.pluginInfo else None,
        }
