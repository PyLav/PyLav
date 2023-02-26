from __future__ import annotations

from pathlib import Path

import discord
from discord import app_commands
from redbot.core import commands
from redbot.core.i18n import Translator

from pylav.core.context import PyLavContext
from pylav.extension.red import errors
from pylav.extension.red.errors import NotDJError, UnauthorizedChannelError
from pylav.type_hints.bot import DISCORD_BOT_TYPE, DISCORD_INTERACTION_TYPE

_ = Translator("PyLav", Path(__file__))


def always_hidden(slash: bool = False):
    async def pred(__: DISCORD_INTERACTION_TYPE | PyLavContext) -> bool:
        return False

    return app_commands.check(pred) if slash else commands.check(pred)


def requires_player(slash: bool = False):
    async def pred(context: PyLavContext | DISCORD_INTERACTION_TYPE):
        if isinstance(context, discord.Interaction):
            if not context.response.is_done():
                await context.response.defer(ephemeral=True)
            bot = context.client
            _lavalink = getattr(bot, "pylav", None)
            player = _lavalink.get_player(context.guild) if _lavalink else None
        else:
            bot = context.bot
            _lavalink = getattr(bot, "pylav", None)
            player = _lavalink.get_player(context.guild) if _lavalink else None
        if not _lavalink:
            return False
        if not player:
            raise errors.MediaPlayerNotFoundError(context)
        return True

    return app_commands.check(pred) if slash else commands.check(pred)


def can_run_command_in_channel(slash: bool = False):
    async def pred(context: PyLavContext | DISCORD_INTERACTION_TYPE):
        if isinstance(context, discord.Interaction):
            if not context.response.is_done():
                await context.response.defer(ephemeral=True)
            bot = context.client
            _lavalink = getattr(bot, "pylav", None)
            player = _lavalink.get_player(context.guild) if _lavalink else None
        else:
            bot = context.bot
            _lavalink = getattr(bot, "pylav", None)
            player = _lavalink.get_player(context.guild) if _lavalink else None
        if not _lavalink:
            return False
        if not context.guild:
            return True
        if player:
            config = player.config
        else:
            config = bot.pylav.player_config_manager.get_config(context.guild.id)

        if (channel_id := await config.fetch_text_channel_id()) != 0 and channel_id != context.channel.id:
            raise UnauthorizedChannelError(channel=channel_id)
        return True

    return app_commands.check(pred) if slash else commands.check(pred)


async def is_dj_logic(
    context: PyLavContext | DISCORD_INTERACTION_TYPE | discord.Message, bot: DISCORD_BOT_TYPE | None = None
) -> bool | None:
    guild = context.guild
    if isinstance(context, discord.Interaction):
        if not context.response.is_done():
            await context.response.defer(ephemeral=True)
        bot = bot or context.client
        author = context.user
    else:
        bot = bot or context.bot
        author = context.author
    return await bot.pylav.is_dj(user=author, guild=guild, additional_role_ids=None, additional_user_ids={*bot.owner_ids, guild.owner_id}) if guild else False  # type: ignore


def invoker_is_dj(slash: bool = False):
    async def pred(context: PyLavContext | DISCORD_INTERACTION_TYPE):
        is_dj = await is_dj_logic(context)
        if is_dj is False:
            raise NotDJError(
                context,
            )
        return True

    return app_commands.check(pred) if slash else commands.check(pred)
