from __future__ import annotations

import logging
import os

from red_commons.logging import RedTraceLogger  # type: ignore
from red_commons.logging import getLogger as redgetLogger
from red_commons.logging import maybe_update_logger_class

__all__ = ("getLogger",)

maybe_update_logger_class()

LOGGER_PREFIX = os.getenv("PYLAV__LOGGER_PREFIX", "")
__deepdiff = logging.getLogger("deepdiff.diff")
__deepdiff.setLevel(logging.CRITICAL)
__deepdiff.propagate = False
__deepdiff.disabled = True
__watchfiles = logging.getLogger("watchfiles")
__watchfiles.setLevel(logging.CRITICAL)
__watchfiles.propagate = False
__watchfiles.disabled = True
logging.getLogger("apscheduler").setLevel(logging.ERROR)
logging.getLogger("aiohttp_client_cache").setLevel(logging.ERROR)


# noinspection PyPep8Naming
def getLogger(name: str) -> RedTraceLogger:  # noqa: N802
    """Get a logger with the prefix set in the environment variable PYLAV__LOGGER_PREFIX."""
    return redgetLogger(f"{LOGGER_PREFIX}{name}")
