from __future__ import annotations

import secrets

from pylav import __version__

# noinspection SpellCheckingInspection
NODE_DEFAULT_SETTINGS = {
    "server": {"port": 2154, "address": "localhost"},
    "lavalink": {
        "plugins": [
            {
                "dependency": "com.github.TopiSenpai.LavaSrc:lavasrc-plugin:3.1.6",
                "repository": "https://jitpack.io",
            },
            {
                "dependency": "com.dunctebot:skybot-lavalink-plugin:1.4.1",
                "repository": "https://m2.duncte123.dev/releases",
            },
            {"dependency": "com.github.topisenpai:sponsorblock-plugin:1.0.4", "repository": "https://jitpack.io"},
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
            "playerUpdateInterval": 5,
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
                "ytsearch:%QUERY%",
                "dzsearch:%QUERY%",
                "ytmsearch:%QUERY%",
                "scsearch:%QUERY%",
            ],
            "sources": {"spotify": False, "applemusic": True, "deezer": False, "yandexmusic": False},
            "spotify": {
                "clientId": "",
                "clientSecret": "",
                "countryCode": "US",
            },
            "applemusic": {"countryCode": "US", "mediaAPIToken": None},
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
