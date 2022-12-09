from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, Union

import discord

if TYPE_CHECKING:
    from discord import app_commands
    from discord.ext.commands import AutoShardedBot, Cog, CommandError, Context

    from pylav.core.context import PyLavContext

    try:
        from redbot.core.bot import Red
        from redbot.core.bot import Red as BotClient
        from redbot.core.commands import Cog as RedCog
        from redbot.core.commands import Context as ClientContext
    except ImportError:
        BotClient = Red = AutoShardedBot
        RedCog = Cog
        ClientContext = Context


else:
    from discord import app_commands
    from discord.ext.commands import Cog, CommandError

    try:
        from redbot.core.bot import Red as BotClient
        from redbot.core.commands import Cog as RedCog
    except ImportError:
        from discord.ext.commands import AutoShardedBot as BotClient

        RedCog = Cog


class BotClientWithLavalinkType(BotClient):
    _pylav_client: Client
    lavalink: Client
    pylav: Client

    async def get_context(
        self, message: discord.abc.Message | DISCORD_INTERACTION_TYPE, *, cls: type[PyLavContext] = None
    ) -> PyLavContext[Any]:
        ...


class InteractionType(discord.Interaction):
    client: BotClientWithLavalinkType
    response: discord.InteractionResponse
    followup: discord.Webhook
    command: app_commands.Command[Any, ..., Any] | app_commands.ContextMenu | None
    channel: discord.interactions.InteractionChannel | None


class PyLavCogType(RedCog):
    __version__: str
    bot: DISCORD_BOT_TYPE
    lavalink: Client
    pylav: Client


DISCORD_BOT_TYPE = TypeVar("DISCORD_BOT_TYPE", bound=BotClientWithLavalinkType, covariant=True)
DISCORD_CONTEXT_TYPE = TypeVar("DISCORD_CONTEXT_TYPE", bound="PyLavContext", covariant=True)
DISCORD_INTERACTION_TYPE = TypeVar("DISCORD_INTERACTION_TYPE", bound=InteractionType, covariant=True)
DISCORD_COG_TYPE = TypeVar("DISCORD_COG_TYPE", bound=PyLavCogType, covariant=True)
DISCORD_COMMAND_ERROR_TYPE = TypeVar(
    "DISCORD_COMMAND_ERROR_TYPE", bound=Union[CommandError, app_commands.errors.AppCommandError], covariant=True
)
