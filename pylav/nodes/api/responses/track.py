from __future__ import annotations

import dataclasses
from typing import NotRequired  # noqa

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
            "info": self.info.to_dict(),
            "encoded": self.encoded,
            "pluginInfo": self.pluginInfo.to_dict() if self.pluginInfo else None,
        }

    def to_database(self) -> dict[str, JSON_DICT_TYPE]:
        return {
            TrackRow.encoded._meta.db_column_name: self.encoded,
            TrackRow.pluginInfo._meta.db_column_name: self.pluginInfo.to_dict() if self.pluginInfo else None,
            TrackRow.info._meta.db_column_name: self.info.to_dict(),
        }
