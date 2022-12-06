from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, TypeVar

import discord

if TYPE_CHECKING:
    from discord import app_commands  # noqa: F401
    from discord.ext.commands import AutoShardedBot, Bot, Cog, CommandError, Context  # noqa: F401

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
    try:
        from redbot.core import commands
        from redbot.core.bot import Red as BotClient
    except ImportError:
        from discord.ext import commands
        from discord.ext.commands import AutoShardedBot as BotClient


class BotClientWithLavalink(BotClient):
    _pylav_client: Client
    lavalink: Client
    pylav: Client

    async def get_context(
        self, message: discord.abc.Message | INTERACTION_TYPE, *, cls: type[PyLavContext] = None
    ) -> PyLavContext[Any]:
        ...


class _InteractionType(discord.Interaction):
    client: BotClientWithLavalink
    response: discord.InteractionResponse
    followup: discord.Webhook
    command: app_commands.Command[Any, ..., Any] | app_commands.ContextMenu | None
    channel: discord.interactions.InteractionChannel | None


class PyLavCogMixin(ABC):
    __version__: str
    bot: DISCORD_BOT_TYPE
    lavalink: Client
    pylav: Client

    @commands.command()
    async def command_play(self, context: PyLavContext, *, query: str = None):
        ...


DISCORD_BOT_TYPE = TypeVar("DISCORD_BOT_TYPE", bound=BotClientWithLavalink, covariant=True)
DISCORD_CONTEXT_TYPE = TypeVar("DISCORD_CONTEXT_TYPE", bound="PyLavContext[Any] | ClientContext[Any] | Context[Any]")
DISCORD_INTERACTION_TYPE = TypeVar("DISCORD_INTERACTION_TYPE", bound="Union[_InteractionType, discord.Interaction]")
DISCORD_COG_TYPE = TypeVar("DISCORD_COG_TYPE", bound="PyLavCogMixin | RedCog | Cog")
DISCORD_COMMAND_ERROR_TYPE = TypeVar("DISCORD_COMMAND_ERROR_TYPE", bound="CommandError")
