from __future__ import annotations

import re

from packaging.version import parse as parse_version

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

SUPPORTED_SEARCHES = {
    "ytmsearch": "YouTube Music",
    "ytsearch": "YouTube",
    "spsearch": "Spotify",
    "scsearch": "SoundCloud",
    "amsearch": "Apple Music",
    "dzsearch": "Deezer",
}

SUPPORTED_SOURCES = {
    # https://github.com/freyacodes/Lavalink
    "youtube",
    "soundcloud",
    "bandcamp",
    "twitch",
    "vimeo",
    "local",
    "http",
    # https://github.com/DuncteBot/skybot-lavalink-plugin
    "getyarn.io",
    "clypit",
    "speak",
    "pornhub",
    "reddit",
    "ocremix",
    "tiktok",
    "mixcloud",
    "soundgasm",
    # https://github.com/TopiSenpai/LavaSrc
    "spotify",
    "applemusic",
    "deezer",
    "yandexmusic",
    # https://github.com/DuncteBot/tts-plugin
    "gcloud-tts",
}

SUPPORTED_FEATURES = {
    # https://github.com/Topis-Lavalink-Plugins/Sponsorblock-Plugin
    "sponsorblock",
}


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
    "disabled_sources": ["local", "http"],
    "temporary": True,
    "extras": {},
    "yaml": {
        "server": {},
        "lavalink": {"server": {"password": "..."}},
    },
}
PYLAV_NODE_SETTINGS["yaml"]["server"]["port"] = PYLAV_NODE_SETTINGS["port"]

BUNDLED_NODES_IDS_HOST_MAPPING = {
    1: "ll-gb.draper.wtf",
    2: "ll-us-ny.draper.wtf",
    1001: "lava.link",
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
        "disabled_sources": ["local"],
        "temporary": True,
        "extras": {},
        "yaml": {
            "server": {},
            "lavalink": {"server": {"password": "..."}},
        },
    },
}
PYLAV_BUNDLED_NODES_SETTINGS["ll-gb.draper.wtf"]["yaml"]["server"]["address"] = PYLAV_BUNDLED_NODES_SETTINGS["ll-gb.draper.wtf"]["host"]  # type: ignore


PYLAV_BUNDLED_NODES_SETTINGS["ll-us-ny.draper.wtf"]["yaml"]["server"]["address"] = PYLAV_BUNDLED_NODES_SETTINGS["ll-us-ny.draper.wtf"]["host"]  # type: ignore

PYLAV_BUNDLED_NODES_SETTINGS["lava.link"]["yaml"]["server"]["address"] = PYLAV_BUNDLED_NODES_SETTINGS["lava.link"]["host"]  # type: ignore
PYLAV_BUNDLED_NODES_SETTINGS["lava.link"]["yaml"]["server"]["port"] = PYLAV_BUNDLED_NODES_SETTINGS["lava.link"]["port"]  # type: ignore


VERSION_ZERO = parse_version("0.0.0")

SNAPSHOT_REGEX = re.compile(r"^(?P<commit>.*?)-SNAPSHOT$")

BUNDLED_PYLAV_PLAYLISTS_IDS = {1, 2}
BUNDLED_SPOTIFY_PLAYLIST_IDS = {1000001, 1000002, 1000003, 1000004}
BUNDLED_DEEZER_PLAYLIST_IDS = set(range(2000001, 2000073))

BUNDLED_PLAYLIST_IDS = BUNDLED_PYLAV_PLAYLISTS_IDS | BUNDLED_SPOTIFY_PLAYLIST_IDS | BUNDLED_DEEZER_PLAYLIST_IDS

BUNDLED_PYLAV_PLAYLISTS = {
    1: (
        "[YT] Aikaterna's curated tracks",
        "https://gist.githubusercontent.com/Drapersniper/" "cbe10d7053c844f8c69637bb4fd9c5c3/raw/playlist.pylav",
    ),
    2: (
        "[YT] Anime OPs/EDs",
        "https://gist.githubusercontent.com/Drapersniper/" "2ad7c4cdd4519d9707f1a65d685fb95f/raw/anime_pl.pylav",
    ),
}
BUNDLED_SPOTIFY_PLAYLIST = {
    1000001: (
        # Predä
        ("2seaovjQuA2cMgltyLQUtd", "[SP] CYBER//", "SP")
    ),
    1000002: (
        # Predä
        ("0rSd8LoXBD5tEBbSsbXqbc", "[SP] PHONK//", "SP")
    ),
    1000003: (
        # Predä
        ("21trhbHm5hVgosPS1YpwSM", "[SP] bangers", "SP")
    ),
}

BUNDLED_DEEZER_PLAYLIST = {
    1000004: ("0BbMjMQZ43vtdz7al266XH", "[SP] ???", "SP"),
    2000001: ("3155776842", "[DZ] Top Worldwide", "DZ"),
    2000002: ("1652248171", "[DZ] Top Canada", "DZ"),
    2000003: ("1362528775", "[DZ] Top South Africa", "DZ"),
    2000004: ("1362527605", "[DZ] Top Venezuela", "DZ"),
    2000005: ("1362526495", "[DZ] Top Ukraine", "DZ"),
    2000006: ("1362525375", "[DZ] Top Tunisia", "DZ"),
    2000007: ("1362524475", "[DZ] Top Thailand", "DZ"),
    2000008: ("1362523615", "[DZ] Top El Salvador", "DZ"),
    2000009: ("1362523075", "[DZ] Top Senegal", "DZ"),
    2000010: ("1362522355", "[DZ] Top Slovenia", "DZ"),
    2000011: ("1362521285", "[DZ] Top Saudi Arabia", "DZ"),
    2000012: ("1362520135", "[DZ] Top Paraguay", "DZ"),
    2000013: ("1362519755", "[DZ] Top Portugal", "DZ"),
    2000014: ("1362518895", "[DZ] Top Philippines", "DZ"),
    2000015: ("1362518525", "[DZ] Top Peru", "DZ"),
    2000016: ("1362516565", "[DZ] Top Nigeria", "DZ"),
    2000017: ("1362510315", "[DZ] Top South Korea", "DZ"),
    2000018: ("1362511155", "[DZ] Top Lebanon", "DZ"),
    2000019: ("1362512715", "[DZ] Top Morocco", "DZ"),
    2000020: ("1362515675", "[DZ] Top Malaysia", "DZ"),
    2000021: ("1362509215", "[DZ] Top Kenya", "DZ"),
    2000022: ("1362508955", "[DZ] Top Japan", "DZ"),
    2000023: ("1362508765", "[DZ] Top Jordan", "DZ"),
    2000024: ("1362508575", "[DZ] Top Jamaica", "DZ"),
    2000025: ("1362501235", "[DZ] Top Ecuador", "DZ"),
    2000026: ("1362501615", "[DZ] Top Egypt", "DZ"),
    2000027: ("1362506695", "[DZ] Top Hungary", "DZ"),
    2000028: ("1362507345", "[DZ] Top Israel", "DZ"),
    2000029: ("1362501015", "[DZ] Top Algeria", "DZ"),
    2000030: ("1362497945", "[DZ] Top Ivory Coast", "DZ"),
    2000031: ("1362495515", "[DZ] Top Bolivia", "DZ"),
    2000032: ("1362494565", "[DZ] Top Bulgaria", "DZ"),
    2000033: ("1362491345", "[DZ] Top United Arab Emirates", "DZ"),
    2000034: ("1313621735", "[DZ] Top USA", "DZ"),
    2000035: ("1313620765", "[DZ] Top Singapore", "DZ"),
    2000036: ("1313620305", "[DZ] Top Sweden", "DZ"),
    2000037: ("1313619885", "[DZ] Top Norway", "DZ"),
    2000038: ("1313619455", "[DZ] Top Ireland", "DZ"),
    2000039: ("1313618905", "[DZ] Top Denmark", "DZ"),
    2000040: ("1313618455", "[DZ] Top Costa Rica", "DZ"),
    2000041: ("1313617925", "[DZ] Top Switzerland", "DZ"),
    2000042: ("1313616925", "[DZ] Top Australia", "DZ"),
    2000043: ("1313615765", "[DZ] Top Austria", "DZ"),
    2000044: ("1279119721", "[DZ] Top Argentina", "DZ"),
    2000045: ("1279119121", "[DZ] Top Chile", "DZ"),
    2000046: ("1279118671", "[DZ] Top Guatemala", "DZ"),
    2000047: ("1279117071", "[DZ] Top Romania", "DZ"),
    2000048: ("1266973701", "[DZ] Top Slovakia", "DZ"),
    2000049: ("1266972981", "[DZ] Top Serbia", "DZ"),
    2000050: ("1266972311", "[DZ] Top Poland", "DZ"),
    2000051: ("1266971851", "[DZ] Top Netherlands", "DZ"),
    2000052: ("1266971131", "[DZ] Top Croatia", "DZ"),
    2000053: ("1266969571", "[DZ] Top Czech Republic", "DZ"),
    2000054: ("1266968331", "[DZ] Top Belgium", "DZ"),
    2000055: ("1221037511", "[DZ] Top Latvia", "DZ"),
    2000056: ("1221037371", "[DZ] Top Lithuania", "DZ"),
    2000057: ("1221037201", "[DZ] Top Estonia", "DZ"),
    2000058: ("1221034071", "[DZ] Top Finland", "DZ"),
    2000059: ("1116190301", "[DZ] Top Honduras", "DZ"),
    2000060: ("1116190041", "[DZ] Top Spain", "DZ"),
    2000061: ("1116189381", "[DZ] Top Russia", "DZ"),
    2000062: ("1116189071", "[DZ] Top Turkey", "DZ"),
    2000063: ("1116188761", "[DZ] Top Indonesia", "DZ"),
    2000064: ("1116188451", "[DZ] Top Colombia", "DZ"),
    2000065: ("1116187241", "[DZ] Top Italy", "DZ"),
    2000066: ("1111143121", "[DZ] Top Germany", "DZ"),
    2000067: ("1111142361", "[DZ] Top Mexico", "DZ"),
    2000068: ("1111142221", "[DZ] Top UK", "DZ"),
    2000069: ("1111141961", "[DZ] Top Brazil", "DZ"),
    2000070: ("1111141961", "[DZ] Top France", "DZ"),
    2000071: (
        "7490833544",
        "[DZ] Best Anime Openings, Endings & Inserts",
        "DZ",
    ),
    2000072: ("5206929684", "[DZ] Japan Anime Hits", "DZ"),
}

BUNDLED_EXTERNAL_PLAYLISTS = BUNDLED_SPOTIFY_PLAYLIST | BUNDLED_DEEZER_PLAYLIST
BUNDLED_PLAYLISTS = BUNDLED_PYLAV_PLAYLISTS | BUNDLED_EXTERNAL_PLAYLISTS
