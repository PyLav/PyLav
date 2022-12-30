from __future__ import annotations

import dataclasses
import typing

from packaging.version import Version as _Version
from packaging.version import parse

from pylav.constants.regex import GIT_SHA1, SEMANTIC_VERSIONING
from pylav.constants.versions import API_DEVELOPMENT_VERSION


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Version:
    semver: str
    major: int
    minor: int
    patch: int
    preRelease: str | None = None

    def __post_init__(self) -> None:
        if not SEMANTIC_VERSIONING.match(self.semver):
            sha1 = GIT_SHA1.search(self.semver)
            sha1 = sha1.group("sha1") if sha1 else "unknown"
            version = _Version(f"{API_DEVELOPMENT_VERSION}+{sha1}")
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
