from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from pylav.client import Client


class UpdateSchemaManager:
    def __init__(self, client: Client):
        self._client = client

    async def run_updates(self):
        """Run through schema migrations."""

        if (await self._client.lib_db_manager.get_bot_db_version()).version == parse_version("0.0.0.0"):
            # FIXME: This should be whatever value the first release is or alternatively `self._client.lib_version`
            await self._client.lib_db_manager.update_bot_dv_version("0.0.0.1")
