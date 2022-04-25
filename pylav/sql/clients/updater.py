from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pylav.client import Client


class UpdateSchemaManager:
    def __init__(self, client: Client):
        self._client = client

    async def run_updates(self):
        """Run through schema migrations."""
