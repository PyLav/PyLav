from __future__ import annotations

import re

from red_commons.logging import getLogger

from pylav.localfiles import _ALL_EXTENSIONS

LOGGER = getLogger("PyLav.ext.Shared.utils.validators")

VALID_ATTACHMENT_EXTENSION = re.compile(rf"^.*\.({'|'.join(i.strip('.') for i in _ALL_EXTENSIONS)})$", re.IGNORECASE)


def valid_query_attachment(attachment_name: str) -> bool:
    return bool(__ := VALID_ATTACHMENT_EXTENSION.match(attachment_name))
