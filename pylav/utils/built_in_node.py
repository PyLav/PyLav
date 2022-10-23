from __future__ import annotations

import base64
import secrets

from pylav import __VERSION__, _ANIME

NODE_DEFAULT_SETTINGS = {
    "server": {"port": 2154, "address": "localhost"},
    "lavalink": {
        "plugins": [
            {
                "dependency": "com.github.TopiSenpai.LavaSrc:lavasrc-plugin:3.0.6",
                "repository": "https://jitpack.io",
            },
            {
                "dependency": "com.dunctebot:skybot-lavalink-plugin:1.4.0",
                "repository": "https://m2.duncte123.dev/releases",
            },
            {"dependency": "com.github.topisenpai:sponsorblock-plugin:v1.0.3", "repository": "https://jitpack.io"},
            {"dependency": "me.rohank05:lavalink-filter-plugin:0.0.1", "repository": "https://jitpack.io"},
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
            "bufferDurationMs": 400,
            "frameBufferDurationMs": 1000,
            "trackStuckThresholdMs": 10000,
            "youtubePlaylistLoadLimit": 100,
            "opusEncodingQuality": 10,
            "resamplingQuality": "LOW",
            "useSeekGhosting": True,
            "playerUpdateInterval": 1,
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
                'ytmsearch:"%ISRC%"',
                'ytsearch:"%ISRC%"',
                "ytmsearch:%QUERY%",
                "ytsearch:%QUERY%",
                "scsearch:%QUERY%",
                "dzisrc:%ISRC%",
                "dzsearch:%QUERY%",
            ],
            # TODO: Add logic to yandex music source
            "sources": {"spotify": True, "applemusic": True, "deezer": True, "yandexmusic": False},
            "spotify": {
                "clientId": "3d5cd36c73924786aa290798b2131c58",
                "clientSecret": "edee5eb255a846fbac8297069debea2e",
                "countryCode": "US",
            },
            "applemusic": {"countryCode": "US"},
            "deezer": {"masterDecryptionKey": "".join([base64.b64decode(r).decode() for r in _ANIME.split(b"|")])},
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
    "sentry": {"dsn": "", "environment": "", "tags": {"pylav_version": __VERSION__}},
    "logging": {
        "file": {"path": "./logs/"},
        "logback": {
            "rollingpolicy": {"max-history": 7, "max-file-size": "25MB", "total-size-cap": "1GB"},
        },
        "level": {"root": "INFO", "lavalink": "INFO"},
    },
}
