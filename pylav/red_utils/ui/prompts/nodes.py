from __future__ import annotations

import asyncio
from pathlib import Path

from redbot.core.i18n import Translator

from pylav.node import Node
from pylav.red_utils.ui.menus.nodes import NodePickerMenu
from pylav.red_utils.ui.selectors.nodes import NodeSelectSelector
from pylav.red_utils.ui.sources.nodes import NodePickerSource
from pylav.types import CogT
from pylav.utils import PyLavContext, translation_shortener

_ = Translator("PyLav", Path(__file__))


async def maybe_prompt_for_node(cog: CogT, context: PyLavContext, nodes: list[Node]) -> Node | None:
    if len(nodes) > 1:
        node_picker = NodePickerMenu(
            cog=cog,
            bot=cog.bot,
            source=NodePickerSource(
                guild_id=context.guild.id,
                cog=cog,
                pages=nodes,
                message_str=translation_shortener(
                    max_length=100, translation=_("Multiple nodes matched, pick the one which you meant")
                ),
            ),
            selector_cls=NodeSelectSelector,
            delete_after_timeout=True,
            clear_buttons_after=True,
            starting_page=0,
            selector_text=translation_shortener(max_length=100, translation=_("Pick a node")),
            original_author=context.interaction.user if context.interaction else context.author,
        )

        await node_picker.start(context)
        try:
            await node_picker.wait_for_response()
            node = node_picker.result
        except asyncio.TimeoutError:
            node = None
    else:
        node = nodes[0]
    return node
