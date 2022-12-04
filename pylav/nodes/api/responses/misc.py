from __future__ import annotations

import dataclasses
import typing

from packaging.version import Version as _Version
from packaging.version import parse

from pylav.constants.regex import VERSION_SNAPSHOT
from pylav.constants.versions import API_DEVELOPMENT_VERSION


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Version:
    semver: str
    major: int
    minor: int
    patch: int
    preRelease: str | None = None

    def __post_init__(self) -> None:
        if match := VERSION_SNAPSHOT.match(self.semver):
            version = _Version(f"{API_DEVELOPMENT_VERSION}+{match.group('commit')}")
        else:
            version = typing.cast(_Version, parse(self.semver))
        object.__setattr__(self, "semver", version)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Git:
    branch: str
    commit: str
    commitTime: int


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Plugin:
    name: str
    version: str
