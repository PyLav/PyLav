from __future__ import annotations

import re

from pylav.logging import getLogger
from pylav.players.query.local_files import ALL_EXTENSIONS

LOGGER = getLogger("PyLav.ext.red.utils.validators")
VALID_ATTACHMENT_EXTENSION = re.compile(rf"^.*\.({'|'.join(i.strip('.') for i in ALL_EXTENSIONS)})$", re.IGNORECASE)


def valid_query_attachment(attachment_name: str) -> bool:
    return bool(__ := VALID_ATTACHMENT_EXTENSION.match(attachment_name))
