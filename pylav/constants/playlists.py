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
        ("2seaovjQuA2cMgltyLQUtd", "[SP] CYBER//", "SP", "playlist")
    ),
    1000002: (
        # Predä
        ("0rSd8LoXBD5tEBbSsbXqbc", "[SP] PHONK//", "SP", "playlist")
    ),
    1000003: (
        # Predä
        ("21trhbHm5hVgosPS1YpwSM", "[SP] bangers", "SP", "playlist")
    ),
    1000004: ("0BbMjMQZ43vtdz7al266XH", "[SP] ???", "SP", "playlist"),
}

BUNDLED_DEEZER_PLAYLIST = {
    2000001: ("3155776842", "[DZ] Top Worldwide", "DZ", "playlist"),
    2000002: ("1652248171", "[DZ] Top Canada", "DZ", "playlist"),
    2000003: ("1362528775", "[DZ] Top South Africa", "DZ", "playlist"),
    2000004: ("1362527605", "[DZ] Top Venezuela", "DZ", "playlist"),
    2000005: ("1362526495", "[DZ] Top Ukraine", "DZ", "playlist"),
    2000006: ("1362525375", "[DZ] Top Tunisia", "DZ", "playlist"),
    2000007: ("1362524475", "[DZ] Top Thailand", "DZ", "playlist"),
    2000008: ("1362523615", "[DZ] Top El Salvador", "DZ", "playlist"),
    2000009: ("1362523075", "[DZ] Top Senegal", "DZ", "playlist"),
    2000010: ("1362522355", "[DZ] Top Slovenia", "DZ", "playlist"),
    2000011: ("1362521285", "[DZ] Top Saudi Arabia", "DZ", "playlist"),
    2000012: ("1362520135", "[DZ] Top Paraguay", "DZ", "playlist"),
    2000013: ("1362519755", "[DZ] Top Portugal", "DZ", "playlist"),
    2000014: ("1362518895", "[DZ] Top Philippines", "DZ", "playlist"),
    2000015: ("1362518525", "[DZ] Top Peru", "DZ", "playlist"),
    2000016: ("1362516565", "[DZ] Top Nigeria", "DZ", "playlist"),
    2000017: ("1362510315", "[DZ] Top South Korea", "DZ", "playlist"),
    2000018: ("1362511155", "[DZ] Top Lebanon", "DZ", "playlist"),
    2000019: ("1362512715", "[DZ] Top Morocco", "DZ", "playlist"),
    2000020: ("1362515675", "[DZ] Top Malaysia", "DZ", "playlist"),
    2000021: ("1362509215", "[DZ] Top Kenya", "DZ", "playlist"),
    2000022: ("1362508955", "[DZ] Top Japan", "DZ", "playlist"),
    2000023: ("1362508765", "[DZ] Top Jordan", "DZ", "playlist"),
    2000024: ("1362508575", "[DZ] Top Jamaica", "DZ", "playlist"),
    2000025: ("1362501235", "[DZ] Top Ecuador", "DZ", "playlist"),
    2000026: ("1362501615", "[DZ] Top Egypt", "DZ", "playlist"),
    2000027: ("1362506695", "[DZ] Top Hungary", "DZ", "playlist"),
    2000028: ("1362507345", "[DZ] Top Israel", "DZ", "playlist"),
    2000029: ("1362501015", "[DZ] Top Algeria", "DZ", "playlist"),
    2000030: ("1362497945", "[DZ] Top Ivory Coast", "DZ", "playlist"),
    2000031: ("1362495515", "[DZ] Top Bolivia", "DZ", "playlist"),
    2000032: ("1362494565", "[DZ] Top Bulgaria", "DZ", "playlist"),
    2000033: ("1362491345", "[DZ] Top United Arab Emirates", "DZ", "playlist"),
    2000034: ("1313621735", "[DZ] Top USA", "DZ", "playlist"),
    2000035: ("1313620765", "[DZ] Top Singapore", "DZ", "playlist"),
    2000036: ("1313620305", "[DZ] Top Sweden", "DZ", "playlist"),
    2000037: ("1313619885", "[DZ] Top Norway", "DZ", "playlist"),
    2000038: ("1313619455", "[DZ] Top Ireland", "DZ", "playlist"),
    2000039: ("1313618905", "[DZ] Top Denmark", "DZ", "playlist"),
    2000040: ("1313618455", "[DZ] Top Costa Rica", "DZ", "playlist"),
    2000041: ("1313617925", "[DZ] Top Switzerland", "DZ", "playlist"),
    2000042: ("1313616925", "[DZ] Top Australia", "DZ", "playlist"),
    2000043: ("1313615765", "[DZ] Top Austria", "DZ", "playlist"),
    2000044: ("1279119721", "[DZ] Top Argentina", "DZ", "playlist"),
    2000045: ("1279119121", "[DZ] Top Chile", "DZ", "playlist"),
    2000046: ("1279118671", "[DZ] Top Guatemala", "DZ", "playlist"),
    2000047: ("1279117071", "[DZ] Top Romania", "DZ", "playlist"),
    2000048: ("1266973701", "[DZ] Top Slovakia", "DZ", "playlist"),
    2000049: ("1266972981", "[DZ] Top Serbia", "DZ", "playlist"),
    2000050: ("1266972311", "[DZ] Top Poland", "DZ", "playlist"),
    2000051: ("1266971851", "[DZ] Top Netherlands", "DZ", "playlist"),
    2000052: ("1266971131", "[DZ] Top Croatia", "DZ", "playlist"),
    2000053: ("1266969571", "[DZ] Top Czech Republic", "DZ", "playlist"),
    2000054: ("1266968331", "[DZ] Top Belgium", "DZ", "playlist"),
    2000055: ("1221037511", "[DZ] Top Latvia", "DZ", "playlist"),
    2000056: ("1221037371", "[DZ] Top Lithuania", "DZ", "playlist"),
    2000057: ("1221037201", "[DZ] Top Estonia", "DZ", "playlist"),
    2000058: ("1221034071", "[DZ] Top Finland", "DZ", "playlist"),
    2000059: ("1116190301", "[DZ] Top Honduras", "DZ", "playlist"),
    2000060: ("1116190041", "[DZ] Top Spain", "DZ", "playlist"),
    2000061: ("1116189381", "[DZ] Top Russia", "DZ", "playlist"),
    2000062: ("1116189071", "[DZ] Top Turkey", "DZ", "playlist"),
    2000063: ("1116188761", "[DZ] Top Indonesia", "DZ", "playlist"),
    2000064: ("1116188451", "[DZ] Top Colombia", "DZ", "playlist"),
    2000065: ("1116187241", "[DZ] Top Italy", "DZ", "playlist"),
    2000066: ("1111143121", "[DZ] Top Germany", "DZ", "playlist"),
    2000067: ("1111142361", "[DZ] Top Mexico", "DZ", "playlist"),
    2000068: ("1111142221", "[DZ] Top UK", "DZ", "playlist"),
    2000069: ("1111141961", "[DZ] Top Brazil", "DZ", "playlist"),
    2000070: ("1111141961", "[DZ] Top France", "DZ", "playlist"),
    2000071: (
        "7490833544",
        "[DZ] Best Anime Openings, Endings & Inserts",
        "DZ",
        "playlist",
    ),
    2000072: ("5206929684", "[DZ] Japan Anime Hits", "DZ", "playlist"),
    2000073: ("15467484", "[DZ] The Elder Scrolls V: Skyrim: Original Game Soundtrack", "DZ", "album"),
}

BUNDLED_EXTERNAL_PLAYLISTS = BUNDLED_SPOTIFY_PLAYLIST | BUNDLED_DEEZER_PLAYLIST
BUNDLED_PLAYLISTS = BUNDLED_PYLAV_PLAYLISTS | BUNDLED_EXTERNAL_PLAYLISTS
