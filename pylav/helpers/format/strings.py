from __future__ import annotations

import pathlib

try:
    from redbot.core.i18n import Translator  # type: ignore

    _ = Translator("PyLav", pathlib.Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


def shorten_string(string: str, max_length: int, right: bool = True) -> str:
    """Shortens the given string to the given max length and adds an ellipsis."""
    if not string:
        return string
    if len(string) > max_length:
        if right:
            return string[: max_length - 1] + "\N{HORIZONTAL ELLIPSIS}"
        else:
            return string[(max_length - 1) * -1 :] + "\N{HORIZONTAL ELLIPSIS}"
    return string


def format_time_dd_hh_mm_ss(duration: int | float) -> str:
    """Formats to the given time in milliseconds into DD:HH:MM:SS"""
    seconds = int(duration // 1000)
    if seconds == 0:
        return _("Calculating...")
    days, seconds = divmod(seconds, 24 * 60 * 60)
    hours, seconds = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(seconds, 60)
    day = f"{days:02d}:" if days else ""
    hour = f"{hours:02d}:" if hours or day else ""
    minutes = f"{minutes:02d}:"
    sec = f"{seconds:02d}"
    return f"{day}{hour}{minutes}{sec}"


def format_time_string(seconds: int | float) -> str:
    """Formats the given seconds into a time string

    Examples:
        60 -> 1 minute
        3600 -> 1 hour
        3601 -> 1 hour 1 second
        86400 -> 1 day
        86401 -> 1 day 1 second
    """
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    hour = _("hour")
    hours = _("hours")

    minute = _("minute")
    minutes = _("minutes")

    second = _("second")
    seconds = _("seconds")

    day = _("day")
    days = _("days")

    if d > 0:
        return f"{d} {day if d == 1 else days} {h} {hour if h == 1 else hours}"

    elif d == 0 and h > 0:
        return f"{h} {hour if h == 1 else hours} {m} {minute if m == 1 else minutes}"

    elif d == 0 and h == 0 and m > 0:
        return f"{m} {minute if m == 1 else minutes} {s} {second if s == 1 else seconds}"

    elif d == 0 and h == 0 and m == 0 and s >= 0:
        return f"{s} {second if s == 1 else seconds}"
    else:
        return ""
