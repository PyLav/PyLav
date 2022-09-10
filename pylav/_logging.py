from __future__ import annotations

import logging
import os

from red_commons.logging import RedTraceLogger
from red_commons.logging import getLogger as redgetLogger
from red_commons.logging import maybe_update_logger_class

maybe_update_logger_class()

LOGGER_PREFIX = os.getenv("PYLAV__LOGGER_PREFIX")

logging.getLogger("deepdiff.diff").setLevel(logging.FATAL)
logging.getLogger("apscheduler.scheduler").setLevel(logging.FATAL)

if LOGGER_PREFIX is None:
    try:
        from redbot.core.utils import AsyncIter  # noqa:

        LOGGER_PREFIX = "red."
    except ImportError:
        LOGGER_PREFIX = ""


def getLogger(name: str) -> RedTraceLogger:
    return redgetLogger(f"{LOGGER_PREFIX}{name}")
