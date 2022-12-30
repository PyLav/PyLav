from __future__ import annotations

__all__ = (
    "BUNDLED_PYLAV_PLAYLISTS_IDS",
    "BUNDLED_SPOTIFY_PLAYLIST_IDS",
    "BUNDLED_DEEZER_PLAYLIST_IDS",
    "BUNDLED_PLAYLIST_IDS",
    "BUNDLED_PYLAV_PLAYLISTS",
    "BUNDLED_SPOTIFY_PLAYLIST",
    "BUNDLED_DEEZER_PLAYLIST",
    "BUNDLED_EXTERNAL_PLAYLISTS",
    "BUNDLED_PLAYLISTS",
)


BUNDLED_PYLAV_PLAYLISTS_IDS = {1, 2}
BUNDLED_SPOTIFY_PLAYLIST_IDS = {1000001, 1000002, 1000003, 1000004}
BUNDLED_DEEZER_PLAYLIST_IDS = set(range(2000001, 2000074))

BUNDLED_PLAYLIST_IDS = BUNDLED_PYLAV_PLAYLISTS_IDS | BUNDLED_SPOTIFY_PLAYLIST_IDS | BUNDLED_DEEZER_PLAYLIST_IDS

# noinspection SpellCheckingInspection
BUNDLED_PYLAV_PLAYLISTS = {
    1: (
        "Aikaterna's curated tracks",
        "https://gist.githubusercontent.com/Drapersniper/cbe10d7053c844f8c69637bb4fd9c5c3/raw/playlist.pylav",
        "YT",
    ),
    2: (
        "Anime OPs/EDs",
        "https://gist.githubusercontent.com/Drapersniper/2ad7c4cdd4519d9707f1a65d685fb95f/raw/anime_pl.pylav",
        "YT",
    ),
}
# noinspection SpellCheckingInspection
BUNDLED_SPOTIFY_PLAYLIST = {
    1000001: ("2seaovjQuA2cMgltyLQUtd", "CYBER//", "playlist"),  # Predä
    1000002: ("0rSd8LoXBD5tEBbSsbXqbc", "PHONK//", "playlist"),  # Predä
    1000003: ("21trhbHm5hVgosPS1YpwSM", "bangers", "playlist"),  # Predä
    1000004: ("0BbMjMQZ43vtdz7al266XH", "???", "playlist"),
}

BUNDLED_DEEZER_PLAYLIST = {
    2000001: ("3155776842", "Top Worldwide", "playlist"),
    2000002: ("1652248171", "Top Canada", "playlist"),
    2000003: ("1362528775", "Top South Africa", "playlist"),
    2000004: ("1362527605", "Top Venezuela", "playlist"),
    2000005: ("1362526495", "Top Ukraine", "playlist"),
    2000006: ("1362525375", "Top Tunisia", "playlist"),
    2000007: ("1362524475", "Top Thailand", "playlist"),
    2000008: ("1362523615", "Top El Salvador", "playlist"),
    2000009: ("1362523075", "Top Senegal", "playlist"),
    2000010: ("1362522355", "Top Slovenia", "playlist"),
    2000011: ("1362521285", "Top Saudi Arabia", "playlist"),
    2000012: ("1362520135", "Top Paraguay", "playlist"),
    2000013: ("1362519755", "Top Portugal", "playlist"),
    2000014: ("1362518895", "Top Philippines", "playlist"),
    2000015: ("1362518525", "Top Peru", "playlist"),
    2000016: ("1362516565", "Top Nigeria", "playlist"),
    2000017: ("1362510315", "Top South Korea", "playlist"),
    2000018: ("1362511155", "Top Lebanon", "playlist"),
    2000019: ("1362512715", "Top Morocco", "playlist"),
    2000020: ("1362515675", "Top Malaysia", "playlist"),
    2000021: ("1362509215", "Top Kenya", "playlist"),
    2000022: ("1362508955", "Top Japan", "playlist"),
    2000023: ("1362508765", "Top Jordan", "playlist"),
    2000024: ("1362508575", "Top Jamaica", "playlist"),
    2000025: ("1362501235", "Top Ecuador", "playlist"),
    2000026: ("1362501615", "Top Egypt", "playlist"),
    2000027: ("1362506695", "Top Hungary", "playlist"),
    2000028: ("1362507345", "Top Israel", "playlist"),
    2000029: ("1362501015", "Top Algeria", "playlist"),
    2000030: ("1362497945", "Top Ivory Coast", "playlist"),
    2000031: ("1362495515", "Top Bolivia", "playlist"),
    2000032: ("1362494565", "Top Bulgaria", "playlist"),
    2000033: ("1362491345", "Top United Arab Emirates", "playlist"),
    2000034: ("1313621735", "Top USA", "playlist"),
    2000035: ("1313620765", "Top Singapore", "playlist"),
    2000036: ("1313620305", "Top Sweden", "playlist"),
    2000037: ("1313619885", "Top Norway", "playlist"),
    2000038: ("1313619455", "Top Ireland", "playlist"),
    2000039: ("1313618905", "Top Denmark", "playlist"),
    2000040: ("1313618455", "Top Costa Rica", "playlist"),
    2000041: ("1313617925", "Top Switzerland", "playlist"),
    2000042: ("1313616925", "Top Australia", "playlist"),
    2000043: ("1313615765", "Top Austria", "playlist"),
    2000044: ("1279119721", "Top Argentina", "playlist"),
    2000045: ("1279119121", "Top Chile", "playlist"),
    2000046: ("1279118671", "Top Guatemala", "playlist"),
    2000047: ("1279117071", "Top Romania", "playlist"),
    2000048: ("1266973701", "Top Slovakia", "playlist"),
    2000049: ("1266972981", "Top Serbia", "playlist"),
    2000050: ("1266972311", "Top Poland", "playlist"),
    2000051: ("1266971851", "Top Netherlands", "playlist"),
    2000052: ("1266971131", "Top Croatia", "playlist"),
    2000053: ("1266969571", "Top Czech Republic", "playlist"),
    2000054: ("1266968331", "Top Belgium", "playlist"),
    2000055: ("1221037511", "Top Latvia", "playlist"),
    2000056: ("1221037371", "Top Lithuania", "playlist"),
    2000057: ("1221037201", "Top Estonia", "playlist"),
    2000058: ("1221034071", "Top Finland", "playlist"),
    2000059: ("1116190301", "Top Honduras", "playlist"),
    2000060: ("1116190041", "Top Spain", "playlist"),
    2000061: ("1116189381", "Top Russia", "playlist"),
    2000062: ("1116189071", "Top Turkey", "playlist"),
    2000063: ("1116188761", "Top Indonesia", "playlist"),
    2000064: ("1116188451", "Top Colombia", "playlist"),
    2000065: ("1116187241", "Top Italy", "playlist"),
    2000066: ("1111143121", "Top Germany", "playlist"),
    2000067: ("1111142361", "Top Mexico", "playlist"),
    2000068: ("1111142221", "Top UK", "playlist"),
    2000069: ("1111141961", "Top Brazil", "playlist"),
    2000070: ("1111141961", "Top France", "playlist"),
    2000071: ("7490833544", "Best Anime Openings, Endings & Inserts", "playlist"),
    2000072: ("5206929684", "Japan Anime Hits", "playlist"),
    2000073: ("15467484", "The Elder Scrolls V: Skyrim: Original Game Soundtrack", "album"),
}

BUNDLED_EXTERNAL_PLAYLISTS = BUNDLED_SPOTIFY_PLAYLIST | BUNDLED_DEEZER_PLAYLIST
BUNDLED_PLAYLISTS = BUNDLED_PYLAV_PLAYLISTS | BUNDLED_EXTERNAL_PLAYLISTS
