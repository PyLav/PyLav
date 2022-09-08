from __future__ import annotations

from pylav._city_dump import US_CITY_DUMP

REGION_TO_COUNTRY_COORDINATE_MAPPING = {}
REGION_TO_COUNTRY_COORDINATE_MAPPING |= US_CITY_DUMP
REGION_TO_COUNTRY_COORDINATE_MAPPING |= {
    "hongkong": (22.2793278, 114.1628131),
    "singapore": (1.357107, 103.8194992),
    "sydney": (-33.8698439, 151.2082848),
    "seattle": (47.608013, -122.335167),
    "japan": (36.5748441, 139.2394179),
    "southafrica": (-28.8166236, 24.991639),
    "india": (22.3511148, 78.6677428),
    "eu": (46.603354, 1.8883335),
    "amsterdam": (52.3727598, 4.8936041),
    "frankfurt": (50.1106444, 8.6820917),
    "russia": (64.6863136, 97.7453061),
    "london": (51.5073219, -0.1276474),
    "us_central": (41.7872548, -87.8410043),
    "us_west": (37.7577627, -122.4727051),
    "us_east": (40.707938, -74.0423759),
    "us_south": (32.7870795, -96.7988588),
    "brazil": (-10.3333333, -53.2),
    "rotterdam": (51.9240069, 4.4777325),
    "santa_clara": (37.3541079, -121.9552368),
    "unknown_pylav": (0, 0),
}

DEFAULT_REGIONS = list(REGION_TO_COUNTRY_COORDINATE_MAPPING.keys())

SUPPORTED_SOURCES = {
    "youtube",
    "soundcloud",
    "twitch",
    "bandcamp",
    "vimeo",
    "http",
    "getyarn",
    "clypit",
    "speak",
    "pornhub",
    "reddit",
    "ocremix",
    "tiktok",
    "mixcloud",
    "soundgasm",
    "gcloud-tts",
    "sponsorblock",
    "local",
    "spotify",
    "applemusic",
}

BUNDLED_PLAYLIST_IDS = {1, 2, 1000001, 1000002, 1000003, 1000004}
BUNDLED_NODES_IDS = {1, 2, 1001}

# Mapping of the PyLav public nodes
PYLAV_NODES = {
    1: ("london", (1.3213765, 103.6956208)),
    2: ("new_york_city", (40.606872, -74.1769477)),
}

PYLAV_NODE_SETTINGS = {
    "port": 443,
    "ssl": True,
    "password": "default",
    "resume_timeout": 600,
    "reconnect_attempts": -1,
    "search_only": False,
    "managed": False,
    "disabled_sources": ["local", "http", "sponsorblock"],
    "temporary": True,
}

PYLAV_BUNDLED_NODES_SETTINGS = {
    "ll-gb.draper.wtf": dict(
        **PYLAV_NODE_SETTINGS, host="ll-gb.draper.wtf", unique_identifier=1, name="PyLav London (Bundled)"
    ),
    "ll-us-ny.draper.wtf": dict(
        **PYLAV_NODE_SETTINGS, host="ll-us-ny.draper.wtf", unique_identifier=2, name="PyLav US-NY (Bundled)"
    ),
    "lava.link": {
        "host": "lava.link",
        "unique_identifier": 1001,
        "name": "Lava.Link (Bundled)",
        "port": 80,
        "resume_timeout": 600,
        "reconnect_attempts": -1,
        "ssl": False,
        "search_only": False,
        "managed": False,
        "disabled_sources": [
            "clypit",
            "reddit",
            "local",
            "tiktok",
            "speak",
            "pornhub",
            "soundgasm",
            "applemusic",
            "mixcloud",
            "sponsorblock",
            "getyarn",
            "spotify",
            "gcloud-tts",
            "ocremix",
        ],
        "temporary": True,
    },
}
