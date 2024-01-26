from __future__ import annotations

__all__ = (
    "SUPPORTED_SEARCHES",
    "SUPPORTED_SOURCES",
    "SUPPORTED_FEATURES",
    "SUPPORTED_FILTERS",
)

# noinspection SpellCheckingInspection
SUPPORTED_SEARCHES = {
    "ytmsearch": "YouTube Music",
    "ytsearch": "YouTube",
    "spsearch": "Spotify",
    "scsearch": "SoundCloud",
    "amsearch": "Apple Music",
    "dzsearch": "Deezer",
}

# noinspection SpellCheckingInspection
SUPPORTED_SOURCES = {
    # https://github.com/lavalink-devs/Lavalink
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
    # https://github.com/topi314/LavaSrc
    "spotify",
    "applemusic",
    "deezer",
    "yandexmusic",
    # https://github.com/DuncteBot/tts-plugin
    "gcloud-tts",
}

SUPPORTED_FEATURES = {
    # https://github.com/topi314/Sponsorblock-Plugin
    "sponsorblock",
    # https://github.com/topi314/LavaSearch
    "lavasearch",
}
SUPPORTED_FILTERS = {
    "distortion",
    "volume",
    "karaoke",
    "echo",
    "equalizer",
    "timescale",
    "tremolo",
    "lowPass",
    "rotation",
    "channelMix",
    "vibrato",
}
