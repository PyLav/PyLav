from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from packaging.version import parse as parse_version

from pylav.constants import BUNDLED_NODES_IDS
from pylav.exceptions import EntryNotFoundError
from pylav.utils.built_in_node import NODE_DEFAULT_SETTINGS

if TYPE_CHECKING:
    from pylav.client import Client


class UpdateSchemaManager:
    __slots__ = ("_client",)

    def __init__(self, client: Client):
        self._client = client

    async def run_updates(self):
        """Run through schema migrations"""
        from pylav import __VERSION__
        from pylav.managed_node import LAVALINK_DOWNLOAD_DIR

        current_version = await self._client.lib_db_manager.get_bot_db_version().fetch_version()
        if current_version == parse_version("0.0.0.0.9999"):
            await self._client.lib_db_manager.update_bot_dv_version(__VERSION__)
            return

        if current_version <= parse_version("0.0.0.1.9999"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            yaml_data["lavalink"]["server"]["trackStuckThresholdMs"] = 10000
            await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.0.0.2")

        if current_version <= parse_version("0.3.1.9999"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            yaml_data["lavalink"]["server"]["opusEncodingQuality"] = 10
            yaml_data["lavalink"]["server"]["resamplingQuality"] = "LOW"
            yaml_data["lavalink"]["server"]["useSeekGhosting"] = True
            await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.3.2")

        if current_version <= parse_version("0.3.2.9999"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            yaml_data["lavalink"]["server"]["youtubeConfig"] = {"email": "", "password": ""}
            await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.3.3")

        if current_version <= parse_version("0.3.3.9999"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            if "soundgasm" not in yaml_data["plugins"]["dunctebot"]["sources"]:
                yaml_data["plugins"]["dunctebot"]["sources"]["soundgasm"] = True

            yaml_data["lavalink"]["plugins"] = NODE_DEFAULT_SETTINGS["lavalink"]["plugins"]
            await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.3.4")

        if current_version <= parse_version("0.3.4.9999"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            if "path" in yaml_data["logging"]:
                yaml_data["logging"]["file"]["path"] = yaml_data["logging"]["path"]
                await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.3.5")

        if current_version <= parse_version("0.3.5.9999"):
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

        if current_version <= parse_version("0.7.5.9999"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            if len(yaml_data["lavalink"]["plugins"]) < len(NODE_DEFAULT_SETTINGS["lavalink"]["plugins"]):
                yaml_data["lavalink"]["plugins"] = NODE_DEFAULT_SETTINGS["lavalink"]["plugins"]
                await config.update_yaml(yaml_data)
            await self._client.lib_db_manager.update_bot_dv_version("0.7.6")

        if current_version <= parse_version("0.8.4.9999"):
            playlists = [p for p in await self._client.playlist_db_manager.get_bundled_playlists() if p.id in {1, 2}]
            for playlist in playlists:
                await playlist.delete()
            await self._client.playlist_db_manager.update_bundled_playlists(1, 2)
            await self._client.lib_db_manager.update_bot_dv_version("0.8.5")

        if current_version <= parse_version("0.8.7.9999"):
            for node_id in BUNDLED_NODES_IDS:
                await self._client.node_db_manager.delete(node_id)
            await self._client.lib_db_manager.update_bot_dv_version("0.8.8")

        if current_version <= parse_version("0.9.1.9999"):
            await self._client.player_state_db_manager.delete_all_players()
            await self._client.lib_db_manager.update_bot_dv_version("0.9.2")

        if current_version <= parse_version("0.10.4.9999"):
            config = self._client.node_db_manager.bundled_node_config()
            yaml_data = await config.fetch_yaml()
            plugins = yaml_data["lavalink"]["plugins"]
            keep = [
                plugin
                for plugin in plugins
                if not plugin["dependency"].startswith(
                    "com.github.Topis-Lavalink-Plugins:Topis-Source-Managers-Plugin:"
                )
            ]
            keep.extend(
                [
                    plugin
                    for plugin in NODE_DEFAULT_SETTINGS["lavalink"]["plugins"]
                    if plugin["dependency"].startswith("com.github.TopiSenpai.LavaSrc:lavasrc-plugin")
                ]
            )
            yaml_data["lavalink"]["plugins"] = keep
            if "topissourcemanagers" in yaml_data["plugins"]:
                yaml_data["plugins"]["lavasrc"] = yaml_data["plugins"]["topissourcemanagers"]
                del yaml_data["plugins"]["topissourcemanagers"]
            await config.update_yaml(yaml_data)
            folder = LAVALINK_DOWNLOAD_DIR / "plugins"
            plugin_files = [
                x
                async for x in folder.iterdir()
                if x.name.startswith("Topis-Source-Managers-Plugin-") and x.suffix == ".jar" and x.is_file()
            ]
            for file in plugin_files:
                with contextlib.suppress(Exception):
                    await file.unlink()

            await self._client.lib_db_manager.update_bot_dv_version("0.10.5")

        with contextlib.suppress(EntryNotFoundError):
            config = self._client.node_db_manager.bundled_node_config()
            await config.update_resume_key(f"PyLav/{self._client.lib_version}-{self._client.bot_id}")
        await self._client.lib_db_manager.update_bot_dv_version(__VERSION__)
