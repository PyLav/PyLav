from __future__ import annotations

import datetime

ASCII_COLOURS = {
    "black": (71, 78, 78),
    "red": (209, 50, 47),
    "green": (110, 149, 11),
    "yellow": (176, 117, 28),
    "blue": (42, 102, 195),
    "magenta": (195, 52, 96),
    "cyan": (42, 157, 132),
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
