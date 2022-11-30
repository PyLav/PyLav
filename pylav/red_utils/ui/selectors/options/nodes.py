from __future__ import annotations

from pathlib import Path

import discord
from redbot.core.i18n import Translator

from pylav.constants import SUPPORTED_FEATURES, SUPPORTED_SOURCES
from pylav.sql.models import NodeModel
from pylav.utils import translation_shortener

_ = Translator("PyLav", Path(__file__))


class SourceOption(discord.SelectOption):
    def __init__(self, name: str, description: str | None, value: str):
        super().__init__(
            label=translation_shortener(max_length=100, translation=name),
            description=translation_shortener(max_length=100, translation=description),
            value=value,
        )


SOURCE_OPTIONS = [
    SourceOption(name=source, description=None, value=source) for source in SUPPORTED_SOURCES.union(SUPPORTED_FEATURES)
]


class NodeOption(discord.SelectOption):
    @classmethod
    async def from_node(cls, node: NodeModel, index: int):
        data = await node.fetch_all()
        return cls(
            label=translation_shortener(max_length=100, translation=f"{index + 1}. {data['name']}"),
            description=translation_shortener(
                max_length=100,
                translation=_("ID: {} || SSL: {} || Search-only: {}").format(node.id, data["ssl"], data["search_only"]),
            ),
            value=f"{node.id}",
        )
