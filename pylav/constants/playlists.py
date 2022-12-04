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
    1000004: ("0BbMjMQZ43vtdz7al266XH", "[SP] ???", "SP"),
}

BUNDLED_DEEZER_PLAYLIST = {
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
