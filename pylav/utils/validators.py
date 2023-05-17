from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pylav.players.query.local_files import LocalFile


def is_url(uri: str | LocalFile) -> bool:
    """Check if the given uri is a url."""
    return f"{uri}".startswith(("https://", "http://", "s3://", "s3a://", "s3n://"))
