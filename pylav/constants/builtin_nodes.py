from __future__ import annotations

__all__ = (
    "PYLAV_NODES",
    "PYLAV_NODE_SETTINGS",
    "BUNDLED_NODES_IDS_HOST_MAPPING",
    "PYLAV_BUNDLED_NODES_SETTINGS",
)

from collections.abc import Mapping
from typing import Any, NotRequired, TypedDict  # noqa


class NodeYaml(TypedDict):
    """The settings for a node."""

    server: dict[str, Any]
    lavalink: dict[str, Any]


class NodeInfo(TypedDict):
    """The info for a node."""

    unique_identifier: NotRequired[int]
    name: NotRequired[str]
    host: NotRequired[str]
    port: int
    ssl: bool
    password: str
    resume_timeout: int
    reconnect_attempts: int
    search_only: bool
    managed: bool
    disabled_sources: list[str]
    temporary: bool
    extras: dict[str, Any]
    yaml: NodeYaml


# Mapping of the PyLav public nodes
PYLAV_NODES: Mapping[int, tuple[str, tuple[float, float]]] = {
    1: ("london", (1.3213765, 103.6956208)),
    2: ("new_york_city", (40.606872, -74.1769477)),
}

PYLAV_NODE_SETTINGS: NodeInfo = {
    "port": 443,
    "ssl": True,
    "password": "default",
    "resume_timeout": 600,
    "reconnect_attempts": -1,
    "search_only": False,
    "managed": False,
    "disabled_sources": ["local", "http"],
    "temporary": True,
    "extras": {},
    "yaml": {
        "server": {},
        "lavalink": {"server": {"password": "..."}},
    },
}
PYLAV_NODE_SETTINGS["yaml"]["server"]["port"] = PYLAV_NODE_SETTINGS["port"]

PYLAV_LONDON_NODE_SETTINGS: NodeInfo = PYLAV_NODE_SETTINGS.copy()
PYLAV_LONDON_NODE_SETTINGS["host"] = "ll-gb.draper.wtf"
PYLAV_LONDON_NODE_SETTINGS["name"] = "PyLav London (Bundled)"
PYLAV_LONDON_NODE_SETTINGS["unique_identifier"] = 1

PYLAV_NY_NODE_SETTINGS: NodeInfo = PYLAV_NODE_SETTINGS.copy()
PYLAV_NY_NODE_SETTINGS["host"] = "ll-us-ny.draper.wtf"
PYLAV_NY_NODE_SETTINGS["name"] = "PyLav US-NY (Bundled)"
PYLAV_NY_NODE_SETTINGS["unique_identifier"] = 2


BUNDLED_NODES_IDS_HOST_MAPPING: Mapping[int, str] = {
    1: "ll-gb.draper.wtf",
    2: "ll-us-ny.draper.wtf",
    1001: "lava.link",
}

PYLAV_BUNDLED_NODES_SETTINGS: Mapping[str, NodeInfo] = {
    "ll-gb.draper.wtf": PYLAV_LONDON_NODE_SETTINGS,
    "ll-us-ny.draper.wtf": PYLAV_NY_NODE_SETTINGS,
    "lava.link": {
        "host": "lava.link",
        "unique_identifier": 1001,
        "name": "Lava.Link (Bundled)",
        "password": "...",
        "port": 80,
        "resume_timeout": 600,
        "reconnect_attempts": -1,
        "ssl": False,
        "search_only": False,
        "managed": False,
        "disabled_sources": ["local"],
        "temporary": True,
        "extras": {},
        "yaml": {
            "server": {},
            "lavalink": {"server": {"password": "..."}},
        },
    },
}
PYLAV_BUNDLED_NODES_SETTINGS["ll-gb.draper.wtf"]["yaml"]["server"]["address"] = PYLAV_BUNDLED_NODES_SETTINGS[
    "ll-gb.draper.wtf"
]["host"]


PYLAV_BUNDLED_NODES_SETTINGS["ll-us-ny.draper.wtf"]["yaml"]["server"]["address"] = PYLAV_BUNDLED_NODES_SETTINGS[
    "ll-us-ny.draper.wtf"
]["host"]

PYLAV_BUNDLED_NODES_SETTINGS["lava.link"]["yaml"]["server"]["address"] = PYLAV_BUNDLED_NODES_SETTINGS["lava.link"][
    "host"
]
PYLAV_BUNDLED_NODES_SETTINGS["lava.link"]["yaml"]["server"]["port"] = PYLAV_BUNDLED_NODES_SETTINGS["lava.link"]["port"]
