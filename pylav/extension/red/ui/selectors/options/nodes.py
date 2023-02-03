from __future__ import annotations

from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav.constants.node_features import SUPPORTED_FEATURES, SUPPORTED_SOURCES
from pylav.helpers.format.strings import shorten_string
from pylav.storage.models.node.real import Node

_ = Translator("PyLav", Path(__file__))


class SourceOption(discord.SelectOption):
    def __init__(self, name: str, description: str | None, value: str):
        super().__init__(
            label=shorten_string(max_length=100, string=name),
            description=shorten_string(max_length=100, string=description),
            value=value,
        )


SOURCE_OPTIONS = [
    SourceOption(name=source, description=None, value=source) for source in SUPPORTED_SOURCES.union(SUPPORTED_FEATURES)
]


class NodeOption(discord.SelectOption):
    @classmethod
    async def from_node(cls, node: Node, index: int):
        data = await node.fetch_all()
        return cls(
            label=shorten_string(max_length=100, string=f"{index + 1}. {data['name']}"),
            description=shorten_string(
                max_length=100,
                string=_(
                    "Identifier: {node_identifier_variable_do_not_translate} || SSL: {node_ssl_variable_do_not_translate} || Search-only: {node_config_variable_do_not_translate}"
                ).format(
                    node_identifier_variable_do_not_translate=node.id,
                    node_ssl_variable_do_not_translate=data["ssl"],
                    node_config_variable_do_not_translate=data["search_only"],
                ),
            ),
            value=f"{node.id}",
        )
