from __future__ import annotations

from datetime import datetime

import pytz


def get_now_utc() -> datetime:
    """A helper function to return an aware UTC datetime representing the current time."""
    return datetime.now(tz=get_tz_utc())


def get_tz_utc() -> pytz.UTC:
    """A helper function to return a pytz.UTC object."""
    return pytz.UTC
