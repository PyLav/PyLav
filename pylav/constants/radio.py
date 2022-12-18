from __future__ import annotations

API_TYPES = {
    "search": {
        "name": str,
        "name_exact": bool,
        "codec": str,
        "codec_exact": bool,
        "country": str,
        "country_exact": bool,
        "countrycode": str,
        "state": str,
        "state_exact": bool,
        "language": str,
        "language_exact": bool,
        "tag": str,
        "tag_exact": bool,
        "tag_list": str,
        "bitrate_min": int,
        "bitrate_max": int,
        "order": str,
        "reverse": bool,
        "offset": int,
        "limit": int,
        "hidebroken": bool,  # Not documented in the "Advanced Station Search"
    },
    "countries": {"code": str},
    "countrycodes": {"code": str},
    "codecs": {"codec": str},
    "states": {"country": str, "state": str},
    "languages": {"language": str},
    "tags": {"tag": str},
}
