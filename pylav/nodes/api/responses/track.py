from __future__ import annotations

import dataclasses
from typing import NotRequired  # noqa

from pylav.constants.node import TRACK_VERSION
from pylav.nodes.api.responses.shared import TrackPluginInfo
from pylav.type_hints.dict_typing import JSON_DICT_TYPE


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Info:
    identifier: str
    isSeekable: bool
    author: str
    length: int = 0
    isStream: bool = False
    position: int | None = 0
    title: str = ""
    uri: str | None = None
    sourceName: str | None = None
    artworkUrl: str | None = None
    isrc: str | None = None
    version: NotRequired[int] = TRACK_VERSION

    def to_dict(self) -> JSON_DICT_TYPE:
        return dataclasses.asdict(self)

    def to_database(self) -> JSON_DICT_TYPE:
        # noinspection SpellCheckingInspection
        return {
            "identifier": self.identifier,
            "title": self.title,
            "uri": self.uri,
            "sourceName": self.sourceName,
            "isrc": self.isrc,
        }


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Track:
    info: Info | dict
    encoded: str | None = None
    pluginInfo: None | dict | TrackPluginInfo = None

    def __post_init__(self) -> None:
        if isinstance(self.pluginInfo, dict):
            object.__setattr__(self, "pluginInfo", TrackPluginInfo(kwargs=self.pluginInfo))
        elif self.pluginInfo is None:
            object.__setattr__(self, "pluginInfo", TrackPluginInfo(kwargs=None))
        if isinstance(self.info, dict):
            object.__setattr__(self, "info", Info(**self.info))

    def set_version(self, version: int) -> None:
        object.__setattr__(self, "version", version)

    def to_dict(self) -> JSON_DICT_TYPE:
        return {
            "info": dataclasses.asdict(self.info),
            "encoded": self.encoded,
            "pluginInfo": dataclasses.asdict(self.pluginInfo) if self.pluginInfo else None,
        }
