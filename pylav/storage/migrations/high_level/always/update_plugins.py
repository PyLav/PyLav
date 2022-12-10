from __future__ import annotations

from typing import TYPE_CHECKING

import ujson
from deepdiff import DeepDiff

from pylav.extension.bundled_node import LAVALINK_DOWNLOAD_DIR
from pylav.storage.migrations.logging import LOGGER

if TYPE_CHECKING:
    from pylav.core.client import Client


async def update_plugins(client: Client) -> None:

    try:
        LOGGER.info("Attempting to update plugins")
        # noinspection PyProtectedMember
        config = client._node_config_manager.bundled_node_config()
        data = await config.fetch_yaml()
        new_plugin_data = []
        _temp = set()
        existing_plugins = set()
        for plugin in data["lavalink"]["plugins"].copy():
            dependency = ":".join(plugin["dependency"].split(":")[:-1])
            if dependency in _temp:
                continue
            _temp.add(dependency)
            if plugin["dependency"].startswith("com.github.TopiSenpai.LavaSrc:lavasrc-plugin:"):
                existing_plugins.add("lavasrc-plugin-")
                org = "TopiSenpai"
                repo = "LavaSrc"
                repository = "https://jitpack.io"
                dependency += ":"
            elif plugin["dependency"].startswith("com.dunctebot:skybot-lavalink-plugin:"):
                existing_plugins.add("skybot-lavalink-plugin-")
                org = "DuncteBot"
                repo = "skybot-lavalink-plugin"
                repository = "https://m2.duncte123.dev/releases"
                dependency += ":"
            elif plugin["dependency"].startswith("com.github.topisenpai:sponsorblock-plugin:"):
                existing_plugins.add("sponsorblock-plugin-")
                org = "Topis-Lavalink-Plugins"
                repo = "Sponsorblock-Plugin"
                repository = "https://jitpack.io"
                dependency += ":"
            elif plugin["dependency"].startswith("com.github.esmBot:lava-xm-plugin:"):
                existing_plugins.add("lava-xm-plugin-")
                org = "esmBot"
                repo = "lava-xm-plugin"
                repository = "https://jitpack.io"
                dependency += ":"
            elif plugin["dependency"].startswith("me.rohank05:lavalink-filter-plugin:"):
                existing_plugins.add("lavalink-filter-plugin-")
                org = "rohank05"
                repo = "lavalink-filter-plugin"
                repository = "https://jitpack.io"
                dependency += ":"
            else:
                continue
            release_data = await (
                await client.cached_session.get(
                    f"https://api.github.com/repos/{org}/{repo}/releases/latest",
                )
            ).json(loads=ujson.loads)
            name = release_data["tag_name"]
            new_plugin_data.append(
                {
                    "dependency": dependency + name,
                    "repository": repository,
                }
            )

        if __ := DeepDiff(
            data["lavalink"]["plugins"], new_plugin_data, ignore_order=True, max_passes=3, cache_size=10000
        ):
            data["lavalink"]["plugins"] = new_plugin_data
            LOGGER.info("New plugin version: %s", new_plugin_data)
            await config.update_yaml(data)
        else:
            LOGGER.info("No plugin updates required")

        folder = LAVALINK_DOWNLOAD_DIR / "plugins"
        if not await folder.exists():
            return
        async for file in folder.iterdir():
            if (
                await file.is_file()
                and file.name.endswith(".jar")
                and not file.name.startswith(tuple(existing_plugins))
            ):
                try:
                    await file.unlink()
                    LOGGER.warning("Removed old plugin: %s", file.name)
                except Exception as exc:
                    LOGGER.error("Failed to remove old plugin: %s", file.name, exc_info=exc)
    except Exception as exc:
        LOGGER.error("Failed to update plugins", exc_info=exc)