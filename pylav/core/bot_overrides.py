from __future__ import annotations

import discord

from pylav.core.context import PyLavContext
from pylav.logging import getLogger
from pylav.type_hints.bot import DISCORD_BOT_TYPE, DISCORD_INTERACTION_TYPE

RED_LOGGER = getLogger("red")
LOGGER = getLogger("PyLav.bot")


async def process_commands(self, message: discord.Message, /):
    """
    Same as base method, but dispatches an additional event for cogs
    which want to handle normal messages differently to command
    messages,  without the overhead of additional get_context calls
    per cog.
    """
    if not message.author.bot:
        ctx = await self.get_context(message, cls=PyLavContext)
        if ctx.invoked_with and isinstance(message.channel, discord.PartialMessageable):
            RED_LOGGER.warning(
                "Discarded a command message (ID: %s) with PartialMessageable channel: %r",
                message.id,
                message.channel,
            )
        else:
            await self.invoke(ctx)
    else:
        ctx = None

    if ctx is None or ctx.valid is False:
        self.dispatch("message_without_command", message)


async def get_context(
    self: DISCORD_BOT_TYPE, message: discord.Message | DISCORD_INTERACTION_TYPE, /, *, cls=PyLavContext
) -> PyLavContext:
    """Get the context for a command invocation."""
    return await super(self.__class__, self).get_context(message, cls=cls)  # noqa
