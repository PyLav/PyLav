from __future__ import annotations

from pathlib import Path

from redbot.core.i18n import Translator

from pylav.core.context import PyLavContext
from pylav.extension.red.ui.menus.nodes import NodePickerMenu
from pylav.extension.red.ui.selectors.nodes import NodeSelectSelector
from pylav.extension.red.ui.sources.nodes import NodePickerSource
from pylav.helpers.format.strings import shorten_string
from pylav.nodes.node import Node
from pylav.type_hints.bot import DISCORD_COG_TYPE

_ = Translator("PyLav", Path(__file__))


async def maybe_prompt_for_node(cog: DISCORD_COG_TYPE, context: PyLavContext, nodes: list[Node]) -> Node | None:
    if len(nodes) > 1:
        node_picker = NodePickerMenu(
            cog=cog,
            bot=cog.bot,
            source=NodePickerSource(
                guild_id=context.guild.id,
                cog=cog,
                pages=nodes,
                message_str=shorten_string(
                    max_length=100, string=_("Multiple nodes matched. Pick the one which you meant.")
                ),
            ),
            selector_cls=NodeSelectSelector,
            delete_after_timeout=True,
            clear_buttons_after=True,
            starting_page=0,
            selector_text=shorten_string(max_length=100, string=_("Pick a node.")),
            original_author=context.interaction.user if context.interaction else context.author,
        )

        await node_picker.start(context)
        try:
            await node_picker.wait_for_response()
            node = node_picker.result
        except TimeoutError:
            node = None
    else:
        node = nodes[0]
    return node
