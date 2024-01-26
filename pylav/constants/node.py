from __future__ import annotations

import multiprocessing
import secrets

from pylav import __version__

MAX_SUPPORTED_API_MAJOR_VERSION = 4
TRACK_VERSION = 3
__CPU_COUNT = multiprocessing.cpu_count()

# noinspection SpellCheckingInspection
NODE_DEFAULT_SETTINGS = {
    "server": {
        "port": 2154,
        "address": "localhost",
        "undertow": {
            "threads": {"io": __CPU_COUNT * 2, "worker": __CPU_COUNT * 64},
        },
        "compression": {"enabled": False},
    },
    "spring": {
        "mvc": {
            "async": {
                "request-timeout": -1,
            }
        }
    },
    "lavalink": {
        "plugins": [
            {
                "dependency": "com.github.topi314.lavasrc:lavasrc-plugin:4.0.1",
            },
            {
                "dependency": "com.github.topi314.sponsorblock:sponsorblock-plugin:3.0.0",
            },
            {
                "dependency": "com.dunctebot:skybot-lavalink-plugin:1.6.3",
            },
            {
                "dependency": "com.github.topi314.lavasearch:lavasearch-plugin:1.0.0",
            },
            {"dependency": "me.rohank05:lavalink-filter-plugin:0.0.2", "repository": "https://jitpack.io"},
            {"dependency": "com.github.esmBot:lava-xm-plugin:v0.2.1", "repository": "https://jitpack.io"},
        ],
        "server": {
            "password": secrets.token_urlsafe(32),
            "sources": {
                "youtube": True,
                "bandcamp": True,
                "soundcloud": True,
                "twitch": True,
                "vimeo": True,
                "http": True,
                "local": True,
            },
            "filters": {
                "volume": True,
                "equalizer": True,
                "karaoke": True,
                "timescale": True,
                "tremolo": True,
                "vibrato": True,
                "distortion": True,
                "rotation": True,
                "channelMix": True,
                "lowPass": True,
                "echo": True,
            },
            "bufferDurationMs": 400,
            "frameBufferDurationMs": 1000,
            "trackStuckThresholdMs": 10000,
            "youtubePlaylistLoadLimit": 100,
            "opusEncodingQuality": 10,
            "resamplingQuality": "HIGH",
            "useSeekGhosting": True,
            "playerUpdateInterval": 30,
            "youtubeSearchEnabled": True,
            "soundcloudSearchEnabled": True,
            "gc-warnings": True,
            "ratelimit": {
                "ipBlocks": [],
                "excludedIps": [],
                "strategy": "RotateOnBan",
                "searchTriggersFail": True,
                "retryLimit": -1,
            },
            "youtubeConfig": {
                "email": "",
                "password": "",
            },
            "httpConfig": {"proxyHost": "", "proxyPort": 0, "proxyUser": "", "proxyPassword": ""},
        },
    },
    "plugins": {
        "lavasrc": {
            "providers": [
                "dzisrc:%ISRC%",
                'ytmsearch:"%ISRC%"',
                'ytsearch:"%ISRC%"',
                "dzsearch:%QUERY%",
                "ytmsearch:%QUERY%",
                "ytsearch:%QUERY%",
                "scsearch:%QUERY%",
            ],
            "sources": {"spotify": False, "applemusic": False, "deezer": False, "yandexmusic": False, "youtube": True},
            "spotify": {
                "clientId": "",
                "clientSecret": "",
                "countryCode": "US",
                "playlistLoadLimit": 110,
                "albumLoadLimit": 220,
            },
            "applemusic": {
                "countryCode": "US",
                "mediaAPIToken": "CHANGEME",
                "playlistLoadLimit": 30,
                "albumLoadLimit": 30,
            },
            "deezer": {"masterDecryptionKey": ""},
            "yandexmusic": {"accessToken": ""},
        },
        "dunctebot": {
            "ttsLanguage": "en-US",
            "sources": {
                "getyarn": True,
                "clypit": True,
                "tts": True,
                "pornhub": True,
                "reddit": True,
                "ocremix": True,
                "tiktok": True,
                "mixcloud": True,
                "soundgasm": True,
            },
        },
    },
    "metrics": {"prometheus": {"enabled": False, "endpoint": "/metrics"}},
    "sentry": {"dsn": "", "environment": "", "tags": {"pylav_version": __version__}},
    "logging": {
        "file": {"path": "./logs/"},
        "logback": {
            "rollingpolicy": {"max-history": 7, "max-file-size": "25MB", "total-size-cap": "1GB"},
        },
        "level": {"root": "INFO", "lavalink": "INFO"},
        "request": {
            "enabled": True,
            "includeClientInfo": True,
            "includeHeaders": False,
            "includeQueryString": True,
            "includePayload": True,
            "maxPayloadLength": 10000,
        },
    },
}
GOOD_RESPONSE_RANGE = range(200, 299)
JAR_SERVER_RELEASES = "https://api.github.com/repos/lavalink-devs/Lavalink/releases"
