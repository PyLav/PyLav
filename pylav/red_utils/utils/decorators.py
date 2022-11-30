from __future__ import annotations

from pathlib import Path

import discord
from discord import app_commands
from redbot.core import commands
from redbot.core.i18n import Translator

from pylav.red_utils import errors
from pylav.red_utils.errors import NotDJError, UnauthorizedChannelError
from pylav.types import InteractionT
from pylav.utils import PyLavContext

_ = Translator("PyLav", Path(__file__))


def always_hidden(slash: bool = False):
    async def pred(__: InteractionT | PyLavContext) -> bool:
        return False

    return app_commands.check(pred) if slash else commands.check(pred)


def requires_player(slash: bool = False):
    async def pred(context: PyLavContext | InteractionT):
        if isinstance(context, discord.Interaction):
            if not context.response.is_done():
                await context.response.defer(ephemeral=True)
            bot = context.client
            _lavalink = getattr(bot, "lavalink", None)
            player = _lavalink.get_player(context.guild) if _lavalink else None
        else:
            bot = context.bot
            _lavalink = getattr(bot, "lavalink", None)
            player = _lavalink.get_player(context.guild) if _lavalink else None
        if not _lavalink:
            return False
        if not player:
            raise errors.MediaPlayerNotFoundError(context)
        return True

    return app_commands.check(pred) if slash else commands.check(pred)


def can_run_command_in_channel(slash: bool = False):
    async def pred(context: PyLavContext | InteractionT):
        if isinstance(context, discord.Interaction):
            if not context.response.is_done():
                await context.response.defer(ephemeral=True)
            bot = context.client
            _lavalink = getattr(bot, "lavalink", None)
            player = _lavalink.get_player(context.guild) if _lavalink else None
        else:
            bot = context.bot
            _lavalink = getattr(bot, "lavalink", None)
            player = _lavalink.get_player(context.guild) if _lavalink else None
        if not _lavalink:
            return False
        if not context.guild:
            return True
        if player:
            config = player.config
        else:
            config = bot.lavalink.player_config_manager.get_config(context.guild.id)

        if (channel_id := await config.fetch_text_channel_id()) != 0 and channel_id != context.channel.id:
            raise UnauthorizedChannelError(channel=channel_id)
        return True

    return app_commands.check(pred) if slash else commands.check(pred)


async def is_dj_logic(context: PyLavContext | InteractionT) -> bool | None:
    guild = context.guild
    if isinstance(context, discord.Interaction):
        if not context.response.is_done():
            await context.response.defer(ephemeral=True)
        bot = context.client
        author = context.user
    else:
        bot = context.bot
        author = context.author
    return await bot.lavalink.is_dj(user=author, guild=guild, additional_role_ids=None, additional_user_ids={*bot.owner_ids, guild.owner_id}, bot=bot) if (getattr(bot, "lavalink", None) and guild) else False  # type: ignore


def invoker_is_dj(slash: bool = False):
    async def pred(context: PyLavContext | InteractionT):
        is_dj = await is_dj_logic(context)
        if is_dj is False:
            raise NotDJError(
                context,
            )
        return True

    return app_commands.check(pred) if slash else commands.check(pred)
