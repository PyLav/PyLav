from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from pylav.client import Client


class UpdateSchemaManager:
    def __init__(self, client: Client):
        self._client = client

    async def run_updates(self):
        """Run through schema migrations."""
        from pylav import EntryNotFoundError
        from pylav._config import __VERSION__

        # FIXME: This should be whatever value the first release is or alternatively `self._client.lib_version`

        if (await self._client.lib_db_manager.get_bot_db_version()).version <= parse_version("0.0.0.0"):
            await self._client.lib_db_manager.update_bot_dv_version("0.0.0.1")

        if (await self._client.lib_db_manager.get_bot_db_version()).version <= parse_version("0.0.0.1"):
            full_data = await self._client.node_db_manager.get_bundled_node_config()
            full_data.yaml["lavalink"]["server"]["trackStuckThresholdMs"] = 10000
            await full_data.save()
            await self._client.lib_db_manager.update_bot_dv_version("0.0.0.2")

        if (await self._client.lib_db_manager.get_bot_db_version()).version <= parse_version("0.3.1"):
            full_data = await self._client.node_db_manager.get_bundled_node_config()
            full_data.yaml["lavalink"]["server"]["opusEncodingQuality"] = 10
            full_data.yaml["lavalink"]["server"]["resamplingQuality"] = "LOW"
            full_data.yaml["lavalink"]["server"]["useSeekGhosting"] = True
            await full_data.save()
            await self._client.lib_db_manager.update_bot_dv_version("0.3.2")

        if (await self._client.lib_db_manager.get_bot_db_version()).version <= parse_version("0.3.2"):
            full_data = await self._client.node_db_manager.get_bundled_node_config()
            full_data.yaml["lavalink"]["server"]["youtubeConfig"] = {"email": "", "password": ""}
            await full_data.save()
            await self._client.lib_db_manager.update_bot_dv_version("0.3.3")

        if (await self._client.lib_db_manager.get_bot_db_version()).version <= parse_version("0.3.3"):
            full_data = await self._client.node_db_manager.get_bundled_node_config()
            if "soundgasm" not in full_data.yaml["plugins"]["dunctebot"]["sources"]:
                full_data.yaml["plugins"]["dunctebot"]["sources"]["soundgasm"] = True

            full_data.yaml["lavalink"]["plugins"] = [
                {
                    "dependency": "com.github.Topis-Lavalink-Plugins:Topis-Source-Managers-Plugin:v2.0.7",
                    "repository": "https://jitpack.io",
                },
                {
                    "dependency": "com.dunctebot:skybot-lavalink-plugin:1.4.0",
                    "repository": "https://m2.duncte123.dev/releases",
                },
                {"dependency": "com.github.topisenpai:sponsorblock-plugin:v1.0.3", "repository": "https://jitpack.io"},
            ]
            await full_data.save()
            await self._client.lib_db_manager.update_bot_dv_version("0.3.4")

        if (await self._client.lib_db_manager.get_bot_db_version()).version <= parse_version("0.3.4"):
            full_data = await self._client.node_db_manager.get_bundled_node_config()
            if "path" in full_data.yaml["logging"]:
                full_data.yaml["logging"]["file"]["path"] = full_data.yaml["logging"]["path"]
                await full_data.save()
            await self._client.lib_db_manager.update_bot_dv_version("0.3.5")

        if (await self._client.lib_db_manager.get_bot_db_version()).version <= parse_version("0.3.5"):
            full_data = await self._client.node_db_manager.get_bundled_node_config()
            if "path" in full_data.yaml["logging"]:
                del full_data.yaml["logging"]["path"]
            if "rollingpolicy" not in full_data.yaml["logging"]["logback"]:
                full_data.yaml["logging"]["logback"] = {
                    "rollingpolicy": {
                        "max-file-size": full_data.yaml["logging"]["file"]["max-size"],
                        "max-history": full_data.yaml["logging"]["file"]["max-history"],
                        "total-size-cap": "1GB",
                    }
                }
            if "max-size" in full_data.yaml["logging"]["file"]:
                del full_data.yaml["logging"]["file"]["max-size"]
            if "max-history" in full_data.yaml["logging"]["file"]:
                del full_data.yaml["logging"]["file"]["max-history"]
            await full_data.save()
            await self._client.lib_db_manager.update_bot_dv_version("0.3.6")
        with contextlib.suppress(EntryNotFoundError):
            bundled_external_node = await self._client.node_db_manager.get_node_config(1)
            bundled_external_node.resume_key = f"PyLav/{self._client.lib_version}-{self._client.bot_id}"
            await bundled_external_node.save()
        await self._client.lib_db_manager.update_bot_dv_version(__VERSION__)
