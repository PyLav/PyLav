from __future__ import annotations

from pylav.constants.regex import SOURCE_INPUT_MATCH_DEEZER, TIMESTAMP_YOUTUBE, YOUTUBE_TRACK_INDEX


def process_youtube(cls: type[Query], query: str, music: bool) -> Query:
    index = 0
    if match := TIMESTAMP_YOUTUBE.search(query):
        start_time = int(match.group(1))
    else:
        start_time = 0
    _has_index = "&index=" in query
    if _has_index and (match := YOUTUBE_TRACK_INDEX.search(query)):
        index = int(match.group(1)) - 1
    if all(k in query for k in ["&list=", "watch?"]):
        query_type = "playlist"
        index = 0
    elif all(x in query for x in ["playlist?"]):
        query_type = "playlist"
    elif any(k in query for k in ["list="]):
        index = 0
        query_type = "single" if _has_index else "playlist"
    else:
        query_type = "single"
    return cls(
        query,
        "YouTube Music" if music else "YouTube",
        start_time=start_time,
        query_type=query_type,
        index=index,
    )


def process_deezer(cls: type[Query], query: str) -> Query:
    """Process a Deezer query."

    Parameters
    ----------
    cls : QueryT
        The class to instantiate.
    query : str
        The query to process.
    Returns
    -------
    Query
        The processed query.
    """
    search = SOURCE_INPUT_MATCH_DEEZER.search(query)
    if search is None:
        raise ValueError("Invalid Deezer query")
    data = search.groupdict()
    # noinspection SpellCheckingInspection
    query_type = data.get("dztype")
    return cls(
        query,
        "Deezer",
        query_type="single" if query_type == "track" else "album" if query_type == "album" else "playlist",
    )


def process_spotify(cls: type[Query], query: str) -> Query:
    query_type = "single"
    if "/playlist/" in query:
        query_type = "playlist"
    elif "/album/" in query:
        query_type = "album"
    return cls(query, "Spotify", query_type=query_type)


def process_soundcloud(cls: type[Query], query: str) -> Query:
    if "/sets/" in query and "?in=" in query or "/sets/" not in query:
        query_type = "single"
    else:
        query_type = "playlist"
    return cls(query, "SoundCloud", query_type=query_type)


def process_bandcamp(cls: type[Query], query: str) -> Query:
    query_type = "album" if "/album/" in query else "single"
    return cls(query, "Bandcamp", query_type=query_type)


def process_yandex_music(cls: type[Query], query: str) -> Query:
    query_type = "single"
    if "/album/" in query and "/track/" not in query:
        query_type = "album"
    elif "/playlist/" in query:
        query_type = "playlist"
    return cls(query, "Yandex Music", query_type=query_type)


from pylav.players.query.obj import Query  # noqa: E305
