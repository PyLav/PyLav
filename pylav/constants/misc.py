from __future__ import annotations

import datetime

ASCII_COLOURS = {
    "black": (1, 1, 1),
    "red": (220, 50, 47),
    "green": (133, 153, 0),
    "yellow": (181, 137, 0),
    "blue": (38, 139, 210),
    "magenta": (211, 54, 130),
    "cyan": (42, 161, 152),
    "white": (255, 255, 255),
}

EQ_BAND_MAPPING = {
    0: "20Hz",
    1: "40Hz",
    2: "63Hz",
    3: "100Hz",
    4: "160Hz",
    5: "250Hz",
    6: "400Hz",
    7: "630Hz",
    8: "1kHz",
    9: "1.6kHz",
    10: "2.5kHz",
    11: "4kHz",
    12: "6.3kHz",
    13: "10kHz",
    14: "16kHz",
}


EPOCH_DT_TZ_AWARE = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
