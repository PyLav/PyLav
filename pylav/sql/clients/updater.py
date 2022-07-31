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
        from pylav._config import __VERSION__

        # FIXME: This should be whatever value the first release is or alternatively `self._client.lib_version`

        if (await self._client.lib_db_manager.get_bot_db_version()).version == parse_version("0.0.0.0"):
            await self._client.lib_db_manager.update_bot_dv_version("0.0.0.1")

        if (await self._client.lib_db_manager.get_bot_db_version()).version == parse_version("0.0.0.1"):
            await self._client.lib_db_manager.update_bot_dv_version("0.0.0.2")
            full_data = await self._client.node_db_manager.get_bundled_node_config()
            full_data.yaml["lavalink"]["server"]["trackStuckThresholdMs"] = 10000
            await full_data.save()

        await self._client.lib_db_manager.update_bot_dv_version(__VERSION__)
