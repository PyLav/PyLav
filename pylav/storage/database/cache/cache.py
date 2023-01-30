from __future__ import annotations

from cashews import Cache  # type: ignore

from pylav.constants.config import READ_CACHING_ENABLED
from pylav.storage.database.cache.logging import LOGGER

if READ_CACHING_ENABLED:
    LOGGER.warning(
        "Caching is enabled, "
        "this will make it so live edits to the database will not be reflected "
        "in the bot until the cache is invalidated or bot is restarted."
    )
else:
    LOGGER.info(
        "Caching is disabled, "
        "this will make it so live edits to the database will be reflected in the bot immediately."
    )


CACHE = Cache("ReadCache")
CACHE.setup("mem://?check_interval=10", size=1_000_000, enable=READ_CACHING_ENABLED)
# TODO: Allow for redis caching
