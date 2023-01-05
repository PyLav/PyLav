from __future__ import annotations

import re

SEMANTIC_VERSIONING = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

GIT_SHA1 = re.compile(r"(?P<sha1>[0-9a-f]{40})")


BASIC_URL_REGEX = re.compile(r"^(https?)://(\S+)$")
STREAM_TITLE = re.compile(rb"StreamTitle='([^']*)';")
SQUARE_BRACKETS = re.compile(r"[\[\]]")
TIME_CONVERTER = re.compile(r"(?:(\d+):)?(\d+):(\d+)")
VOICE_CHANNEL_ENDPOINT = re.compile(r"^(?P<region>.*?)\d+.discord.media:\d+$")

DISCORD_ID = re.compile(r"([0-9]{15,20})$")
DISCORD_USER_MENTION = re.compile(r"<@!?([0-9]{15,20})>$")
DISCORD_CHANNEL_MENTION = re.compile(r"<#([0-9]{15,20})>$")
DISCORD_ROLE_MENTION = re.compile(r"<@&([0-9]{15,20})>$")

JAVA_VERSION_LINE_PRE223 = re.compile(r'version "1\.(?P<major>[0-8])\.(?P<minor>0)(?:_\d+)?(?:-.*)?"')
JAVA_VERSION_LINE_223 = re.compile(r'version "(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.\d+)*(-[a-zA-Z\d]+)?"')
SEMANTIC_VERSION_LAZY = re.compile(
    r"(?P<major>[0-9]|[1-9][0-9]*)\."
    r"(?P<minor>[0-9]|[1-9][0-9]*)\."
    r"(?P<micro>[0-9]|[1-9][0-9]*)"
    r"(?:-(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+)?"
)

LAVALINK_BUILD_LINE = re.compile(rb"Build:\s+(?P<build>\d+|Unknown)")
LAVALINK_BRANCH_LINE = re.compile(rb"Branch\s+(?P<branch>.+?)\n")
LAVALINK_JAVA_LINE = re.compile(rb"JVM:\s+(?P<jvm>.+?)\n")
LAVALINK_LAVAPLAYER_LINE = re.compile(rb"Lavaplayer\s+(?P<lavaplayer>.+?)\n")
LAVALINK_BUILD_TIME_LINE = re.compile(rb"Build time:\s+(?P<build_time>.+?)\n")
LAVALINK_COMMIT_LINE = re.compile(rb"Commit:\s+(?P<commit>.+?)\n")
LAVALINK_VERSION_LINE = re.compile(rb"Version:\s+(?P<version>.+?)\n")
LAVALINK__READY_LINE = re.compile(rb"Lavalink is ready to accept connections")
LAVALINK_FAILED_TO_START = re.compile(rb"Web server failed to start\. (.*)")

# noinspection SpellCheckingInspection
SOURCE_INPUT_MATCH_CLYPIT = re.compile(r"(http://|https://(www.)?)?clyp\.it/(.*)", re.IGNORECASE)
# noinspection SpellCheckingInspection
# https://github.com/Walkyst/lavaplayer-fork/blob/custom/main/src/main/java/com/sedmelluq/discord/lavaplayer/source/getyarn/GetyarnAudioSourceManager.java#L38
SOURCE_INPUT_MATCH_GETYARN = re.compile(r"(?:http://|https://(?:www.)?)?getyarn.io/yarn-clip/(.*)", re.IGNORECASE)
SOURCE_INPUT_MATCH_MIXCLOUD = re.compile(
    r"https?://(?:(?:www|beta|m)\.)?mixcloud.com/([^/]+)/(?!stream|uploads|favorites|listens|playlists)([^/]+)/?",
    re.IGNORECASE,
)
# noinspection SpellCheckingInspection
SOURCE_INPUT_MATCH_OCRREMIX = re.compile(
    r"(?:https?://(?:www\.)?ocremix\.org/remix/)?(?P<ocrmix_id>OCR\d+)(?:.*)?", re.IGNORECASE
)
SOURCE_INPUT_MATCH_PORNHUB = re.compile(
    r"^https?://([a-z]+.)?pornhub\.(com|net)/view_video\.php\?viewkey=([a-zA-Z\d]+).*$", re.IGNORECASE
)
SOURCE_INPUT_MATCH_REDDIT = re.compile(
    r"https://(?:www|old)\.reddit\.com/"
    r"r/[^/]+/[^/]+/([^/]+)"
    r"(?:/?(?:[^/]+)?/?)?|"
    r"https://v\.redd\.it/([^/]+)(?:.*)?",
    re.IGNORECASE,
)
# noinspection SpellCheckingInspection
SOURCE_INPUT_MATCH_SOUNDGASM = re.compile(
    r"https?://soundgasm\.net/u/(?P<soundgasm_path>(?P<soundgasm_author>[^/]+)/[^/]+)", re.IGNORECASE
)
SOURCE_INPUT_MATCH_TIKTOK = re.compile(
    r"^https://(?:www\.|m\.)?tiktok\.com/@(?P<tiktok_user>[^/]+)/video/(?P<tiktok_video>\d+).*$", re.IGNORECASE
)

# https://github.com/TopiSenpai/LavaSrc/blob/master/main/src/main/java/com/github/topisenpai/lavasrc/spotify/SpotifySourceManager.java#L39
SOURCE_INPUT_MATCH_SPOTIFY = re.compile(
    r"(https?://)?(www\.)?open\.spotify\.com/(user/[a-zA-Z\d\-_]+/)?"
    r"(?P<spotify_type>track|album|playlist|artist)/"
    r"(?P<spotify_identifier>[a-zA-Z\d\-_]+)",
    re.IGNORECASE,
)
# https://github.com/TopiSenpai/LavaSrc/blob/master/main/src/main/java/com/github/topisenpai/lavasrc/applemusic/AppleMusicSourceManager.java#L33
SOURCE_INPUT_MATCH_APPLE_MUSIC = re.compile(
    r"(https?://)?(www\.)?music\.apple\.com/(?P<amcountrycode>[a-zA-Z]{2}/)?"
    r"(?P<type>album|playlist|artist|song)(/[a-zA-Z\d\-]+)?/"
    r"(?P<identifier>[a-zA-Z\d\-.]+)"
    r"(\?i=(?P<identifier2>\d+))?",
    re.IGNORECASE,
)
# https://github.com/Walkyst/lavaplayer-fork/blob/custom/main/src/main/java/com/sedmelluq/discord/lavaplayer/source/bandcamp/BandcampAudioSourceManager.java#L39
SOURCE_INPUT_MATCH_BANDCAMP = re.compile(
    r"^(https?://(?:[^.]+\.|)bandcamp\.com)/(track|album)/([a-zA-Z\d\-_]+)/?(?:\?.*|)$", re.IGNORECASE
)
# https://github.com/Walkyst/lavaplayer-fork/blob/custom/main/src/main/java/com/sedmelluq/discord/lavaplayer/source/nico/NicoAudioSourceManager.java#L47
SOURCE_INPUT_MATCH_NICONICO = re.compile(
    r"(?:http://|https://|)(?:www\.|)nicovideo\.jp/watch/(sm\d+)(?:\?.*|)$", re.IGNORECASE
)
# https://github.com/Walkyst/lavaplayer-fork/blob/custom/main/src/main/java/com/sedmelluq/discord/lavaplayer/source/twitch/TwitchStreamAudioSourceManager.java#L43
SOURCE_INPUT_MATCH_TWITCH = re.compile(r"^https://(?:www\.|go\.)?twitch\.tv/([^/]+)$", re.IGNORECASE)
# https://github.com/Walkyst/lavaplayer-fork/blob/custom/main/src/main/java/com/sedmelluq/discord/lavaplayer/source/vimeo/VimeoAudioSourceManager.java#L39
SOURCE_INPUT_MATCH_VIMEO = re.compile(r"^https://vimeo.com/\d+(?:\?.*|)$", re.IGNORECASE)

# noinspection LongLine
SOURCE_INPUT_MATCH_SOUND_CLOUD = re.compile(
    r"^(?:http://|https://|)soundcloud\.app\.goo\.gl/([a-zA-Z0-9-_]+)/?(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/"
    r"([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/?(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/"
    r"([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/s-([a-zA-Z0-9-_]+)(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/"
    r"([a-zA-Z0-9-_]+)/likes/?(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/"
    r"([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)(?:\?.*|)$",
    # This last line was manually added and does not exist in in lavaplayer...
    # https://github.com/Walkyst/lavaplayer-fork/blob/custom/main/src/main/java/com/sedmelluq/discord/lavaplayer/source/soundcloud/SoundCloudAudioSourceManager.java
    re.IGNORECASE,
)
SOURCE_INPUT_MATCH_M3U = re.compile(r"^(?!http).*\.m3u8?$", re.IGNORECASE)
SOURCE_INPUT_MATCH_PLS = re.compile(r"^.*\.pls$", re.IGNORECASE)
SOURCE_INPUT_MATCH_PLS_TRACK = re.compile(r"^File\d+=(?P<pls_query>.+)$", re.IGNORECASE)
SOURCE_INPUT_MATCH_XSPF = re.compile(r"^.*\.xspf$", re.IGNORECASE)
SOURCE_INPUT_MATCH_PYLAV = re.compile(r"^.*\.pylav$", re.IGNORECASE)
# https://github.com/Walkyst/lavaplayer-fork/blob/custom/main/src/main/java/com/sedmelluq/discord/lavaplayer/source/youtube/DefaultYoutubeLinkRouter.java
SOURCE_INPUT_MATCH_YOUTUBE = re.compile(
    r"(?:http://|https://|)(?:www\.|m\.)?(?P<youtube_music>music\.)?youtu(be\.com|\.be)", re.IGNORECASE
)
SOURCE_INPUT_MATCH_SPEAK = re.compile(r"^(?P<speak_source>speak):\s*?(?P<speak_query>.*)$", re.IGNORECASE)
# noinspection SpellCheckingInspection
SOURCE_INPUT_MATCH_GCTSS = re.compile(r"^(?P<gctts_source>tts://)\s*?(?P<gctts_query>.*)$", re.IGNORECASE)
SOURCE_INPUT_MATCH_SEARCH = re.compile(
    r"^((?P<search_source>ytm|yt|sp|sc|am|dz)search|(?P<search_deezer_isrc>dzisrc)):\s*?(?P<search_query>.*)$",
    re.IGNORECASE,
)
SOURCE_INPUT_MATCH_HTTP = re.compile(r"^http(s)?://", re.IGNORECASE)
# https://github.com/TopiSenpai/LavaSrc/blob/master/main/src/main/java/com/github/topisenpai/lavasrc/deezer/DeezerAudioSourceManager.java#L35
SOURCE_INPUT_MATCH_DEEZER = re.compile(
    r"^(https?://)?(www\.)?deezer\.com/"
    r"(?P<dzcountrycode>[a-zA-Z]{2}/)?"
    r"(?P<dztype>track|album|playlist|artist)/"
    r"(?P<dzidentifier>[0-9]+).*$|"
    r"^(https?://)?(www\.)?deezer\.page\.link/.*$",
    re.IGNORECASE,
)
# https://github.com/Walkyst/lavaplayer-fork/blob/custom/main/src/main/java/com/sedmelluq/discord/lavaplayer/source/yamusic/YandexMusicAudioSourceManager.java#L33
# https://github.com/TopiSenpai/LavaSrc/blob/master/main/src/main/java/com/github/topisenpai/lavasrc/yandexmusic/YandexMusicSourceManager.java#L34
SOURCE_INPUT_MATCH_YANDEX_TRACK = re.compile(
    r"^(https?://)?music\.yandex\.ru/(?P<ymtype1>artist|album)/"
    r"(?P<ymidentifier>[0-9]+)/?((?P<ymtype2>track/)(?P<ymidentifier2>[0-9]+)/?)?$"
)
SOURCE_INPUT_MATCH_YANDEX_PLAYLIST = re.compile(
    r"^(https?://)?music\.yandex\.ru/users/(?P<ympidentifier>[0-9A-Za-z@.-]+)/playlists/(?P<ympidentifier2>[0-9]+)/?$"
)
SOURCE_INPUT_MATCH_YANDEX = re.compile(
    "|".join([SOURCE_INPUT_MATCH_YANDEX_TRACK.pattern, SOURCE_INPUT_MATCH_YANDEX_PLAYLIST.pattern])
)

LOCAL_TRACK_NESTED = re.compile(
    r"^(?P<local_recursive>all|nested|recursive|tree):\s*?(?P<local_query>.*)$", re.IGNORECASE
)
SOURCE_INPUT_MATCH_LOCAL_TRACK_URI = re.compile(r"^file://(?P<local_file>.*)$", re.IGNORECASE)
SOURCE_INPUT_MATCH_BASE64_TEST = re.compile(r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$")

SOURCE_INPUT_MATCH_MERGED = re.compile(
    "|".join(
        [
            r.pattern
            for r in [
                SOURCE_INPUT_MATCH_SPOTIFY,
                SOURCE_INPUT_MATCH_APPLE_MUSIC,
                SOURCE_INPUT_MATCH_YOUTUBE,
                SOURCE_INPUT_MATCH_SPEAK,
                SOURCE_INPUT_MATCH_GCTSS,
                SOURCE_INPUT_MATCH_SEARCH,
                SOURCE_INPUT_MATCH_CLYPIT,
                SOURCE_INPUT_MATCH_GETYARN,
                SOURCE_INPUT_MATCH_MIXCLOUD,
                SOURCE_INPUT_MATCH_OCRREMIX,
                SOURCE_INPUT_MATCH_PORNHUB,
                SOURCE_INPUT_MATCH_REDDIT,
                SOURCE_INPUT_MATCH_SOUNDGASM,
                SOURCE_INPUT_MATCH_TIKTOK,
                SOURCE_INPUT_MATCH_BANDCAMP,
                SOURCE_INPUT_MATCH_NICONICO,
                SOURCE_INPUT_MATCH_TWITCH,
                SOURCE_INPUT_MATCH_VIMEO,
                SOURCE_INPUT_MATCH_SOUND_CLOUD,
                SOURCE_INPUT_MATCH_YANDEX,
                SOURCE_INPUT_MATCH_M3U,
                SOURCE_INPUT_MATCH_PLS,
                SOURCE_INPUT_MATCH_PYLAV,
                LOCAL_TRACK_NESTED,
                SOURCE_INPUT_MATCH_LOCAL_TRACK_URI,
                SOURCE_INPUT_MATCH_DEEZER,
                SOURCE_INPUT_MATCH_HTTP,
            ]
        ]
    ),
    re.IGNORECASE,
)

TIMESTAMP_YOUTUBE = re.compile(r"[&?]t=(\d+)s?")
TIMESTAMP_SPOTIFY = re.compile(r"#(\d+):(\d+)")
TIMESTAMP_SOUNDCLOUD = re.compile(r"#t=(\d+):(\d+)s?")
TIMESTAMP_TWITCH = re.compile(r"\?t=(\d+)h(\d+)m(\d+)s")
YOUTUBE_TRACK_INDEX = re.compile(r"&index=(\d+)")
