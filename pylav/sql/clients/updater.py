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
        """Run through schema migrations"""
        from pylav import EntryNotFoundError
        from pylav._config import __VERSION__

        current_version = await self._client.lib_db_manager.get_bot_db_version().fetch_version()
        if current_version == parse_version("0.0.0.0"):
            await self._client.lib_db_manager.update_bot_dv_version(__VERSION__)
            return

        if current_version <= parse_version("0.0.0.1"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            yaml_data["lavalink"]["server"]["trackStuckThresholdMs"] = 10000
            await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.0.0.2")

        if current_version <= parse_version("0.3.1"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            yaml_data["lavalink"]["server"]["opusEncodingQuality"] = 10
            yaml_data["lavalink"]["server"]["resamplingQuality"] = "LOW"
            yaml_data["lavalink"]["server"]["useSeekGhosting"] = True
            await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.3.2")

        if current_version <= parse_version("0.3.2"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            yaml_data["lavalink"]["server"]["youtubeConfig"] = {"email": "", "password": ""}
            await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.3.3")

        if current_version <= parse_version("0.3.3"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            if "soundgasm" not in yaml_data["plugins"]["dunctebot"]["sources"]:
                yaml_data["plugins"]["dunctebot"]["sources"]["soundgasm"] = True

            yaml_data["lavalink"]["plugins"] = [
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
            await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.3.4")

        if current_version <= parse_version("0.3.4"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            if "path" in yaml_data["logging"]:
                yaml_data["logging"]["file"]["path"] = yaml_data["logging"]["path"]
                await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.3.5")

        if current_version <= parse_version("0.3.5"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            if "path" in yaml_data["logging"]:
                del yaml_data["logging"]["path"]
            if "rollingpolicy" not in yaml_data["logging"]["logback"]:
                yaml_data["logging"]["logback"] = {
                    "rollingpolicy": {
                        "max-file-size": yaml_data["logging"]["file"]["max-size"],
                        "max-history": yaml_data["logging"]["file"]["max-history"],
                        "total-size-cap": "1GB",
                    }
                }
            if "max-size" in yaml_data["logging"]["file"]:
                del yaml_data["logging"]["file"]["max-size"]
            if "max-history" in yaml_data["logging"]["file"]:
                del yaml_data["logging"]["file"]["max-history"]
            await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.3.6")
        with contextlib.suppress(EntryNotFoundError):
            config = self._client.node_db_manager.bundled_node_config()
            await config.update_resume_key(f"PyLav/{self._client.lib_version}-{self._client.bot_id}")
        await self._client.lib_db_manager.update_bot_dv_version(__VERSION__)
