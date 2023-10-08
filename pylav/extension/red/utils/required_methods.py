from __future__ import annotations

import asyncio
import contextlib
import inspect
from pathlib import Path
from types import MethodType

import discord
from discord.ext.commands import CheckFailure
from redbot.core import commands
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box
from tabulate import tabulate

from pylav.core.client import Client
from pylav.core.context import PyLavContext
from pylav.exceptions.node import NoNodeAvailableException, NoNodeWithRequestFunctionalityAvailableException
from pylav.extension.red.errors import (
    IncompatibleException,
    MediaPlayerNotFoundError,
    NotDJError,
    UnauthorizedChannelError,
)
from pylav.helpers.format.ascii import EightBitANSI
from pylav.logging import getLogger
from pylav.type_hints.bot import DISCORD_BOT_TYPE, DISCORD_COG_TYPE

_ = Translator("PyLav", Path(__file__))
_LOCK = asyncio.Lock()
LOGGER = getLogger("PyLav.ext.red.utils.overrides")

INCOMPATIBLE_COGS = {}


@commands.command(
    cls=commands.commands._AlwaysAvailableCommand,
    name="plcredits",
    aliases=["pltranslation"],
    i18n=_,
)
async def pylav_credits(context: PyLavContext) -> None:
    """Shows the credits and translation details for the PyLav cogs and shared code"""
    await context.send(
        embed=await context.pylav.construct_embed(
            messageable=context,
            description=_(
                "PyLav was created by {library_author_name_variable_do_not_translate}.\n\n"
                "PyLav source code can be located in {library_url_variable_do_not_translate}\n"
                "PyLav license can be located in {library_license_variable_do_not_translate}\n"
                "PyLav-Cogs source code can be located in {second_library_url_variable_do_not_translate}\n\n"
                "You can join the PyLav support server via {support_server_url_variable_do_not_translate}\n"
                "\n\n"
                "You can help translate PyLav by contributing to our Crowdin project at:\n"
                "{crowdin_project_url_variable_do_not_translate}\n\n\n"
                "Contributors:\n"
                "- {project_contributors_url_variable_do_not_translate}\n"
                "- {second_project_contributors_url_variable_do_not_translate}\n"
                "If you wish to buy me a coffee for my work, you can do so at:\n"
                "{buymeacoffee_url_variable_do_not_translate} or {github_sponsors_url_variable_do_not_translate}"
            ).format(
                library_author_name_variable_do_not_translate="[Draper#6666](https://github.com/Drapersniper)",
                library_url_variable_do_not_translate="https://github.com/PyLav/PyLav",
                library_license_variable_do_not_translate="https://github.com/PyLav/PyLav/blob/develop/LICENSE",
                second_library_url_variable_do_not_translate="https://github.com/PyLav/Red-Cogs",
                support_server_url_variable_do_not_translate="https://discord.com/invite/vnmcXqtgeY",
                crowdin_project_url_variable_do_not_translate="https://crowdin.com/project/pylav",
                project_contributors_url_variable_do_not_translate="https://github.com/PyLav/PyLav/graphs/contributors",
                second_project_contributors_url_variable_do_not_translate="https://github.com/PyLav/Red-Cogs/graphs/contributors",
                buymeacoffee_url_variable_do_not_translate="https://www.buymeacoffee.com/draper",
                github_sponsors_url_variable_do_not_translate="https://github.com/sponsors/Drapersniper",
            ),
        ),
        ephemeral=True,
    )


@commands.command(
    cls=commands.commands._AlwaysAvailableCommand,
    name="plversion",
    aliases=["pylavversion"],
    i18n=_,
)
async def pylav_version(context: PyLavContext) -> None:
    """Show the version of PyLav library"""
    if isinstance(context, discord.Interaction):
        context = await context.client.get_context(context)
    if context.interaction and not context.interaction.response.is_done():
        await context.defer(ephemeral=True)
    data = [
        (EightBitANSI.paint_white("PyLav"), EightBitANSI.paint_blue(context.pylav.lib_version)),
    ]

    await context.send(
        embed=await context.pylav.construct_embed(
            description=box(
                tabulate(
                    data,
                    headers=(
                        EightBitANSI.paint_yellow(_("Library"), bold=True, underline=True),
                        EightBitANSI.paint_yellow(_("Version"), bold=True, underline=True),
                    ),
                    tablefmt="fancy_grid",
                ),
                lang="ansi",
            ),
            messageable=context,
        ),
        ephemeral=True,
    )


def _done_callback(task: asyncio.Task) -> None:
    with contextlib.suppress(asyncio.CancelledError):
        exc = task.exception()
        if exc is not None:
            LOGGER.error("Error in initialize task", exc_info=exc)


async def cog_command_error(self: DISCORD_COG_TYPE, context: PyLavContext, error: Exception) -> None:
    error = getattr(error, "original", error)
    unhandled = True
    if isinstance(error, MediaPlayerNotFoundError):
        unhandled = False
        await context.send(
            embed=await self.pylav.construct_embed(
                messageable=context,
                description=_("This command requires that I be in a voice channel before it can be executed."),
            ),
            ephemeral=True,
        )
    elif isinstance(error, NoNodeAvailableException):
        unhandled = False
        await context.send(
            embed=await self.pylav.construct_embed(
                messageable=context,
                description=_(
                    "PyLavPlayer cog is temporarily unavailable due to an outage with the backend services; please try again later."
                ),
                footer=_("There are no nodes available currently.")
                if await self.bot.is_owner(context.author)
                else None,
            ),
            ephemeral=True,
        )
    elif isinstance(error, NoNodeWithRequestFunctionalityAvailableException):
        unhandled = False
        await context.send(
            embed=await self.pylav.construct_embed(
                messageable=context,
                description=_(
                    "PyLavPlayer is currently unable to process tracks belonging to {feature_name_variable_do_not_translate}."
                ).format(feature_name_variable_do_not_translate=error.feature),
                footer=_(
                    "There is currently no available Lavalink node with the feature {feature_name_variable_do_not_translate}."
                ).format(feature_name_variable_do_not_translate=error.feature)
                if await self.bot.is_owner(context.author)
                else None,
            ),
            ephemeral=True,
        )
    elif isinstance(error, UnauthorizedChannelError):
        unhandled = False
        await context.send(
            embed=await self.pylav.construct_embed(
                messageable=context,
                description=_(
                    "This command is unavailable in this channel; please use {channel_name_variable_do_not_translate} instead."
                ).format(
                    channel_name_variable_do_not_translate=channel.mention
                    if (channel := context.guild.get_channel_or_thread(error.channel))
                    else error.channel
                ),
            ),
            ephemeral=True,
            delete_after=10,
        )
    elif isinstance(error, NotDJError):
        unhandled = False
        await context.send(
            embed=await self.pylav.construct_embed(
                messageable=context,
                description=_("This command requires you to be a disc jockey."),
            ),
            ephemeral=True,
            delete_after=10,
        )
    if unhandled:
        if (meth := getattr(self, "__pylav_original_cog_command_error", None)) and (
            func := self._get_overridden_method(meth)
        ):
            return await discord.utils.maybe_coroutine(func, context, error)
        else:
            return await self.bot.on_command_error(context, error, unhandled_by_cog=True)  # type: ignore


async def cog_unload(self: DISCORD_COG_TYPE) -> None:
    if self._init_task is not None:
        self._init_task.cancel()
    client = self.pylav
    await client.unregister(cog=self)
    if client._shutting_down:
        self.bot.remove_command(pylav_credits.qualified_name)
        self.bot.remove_command(pylav_version.qualified_name)
    if meth := getattr(self, "__pylav_original_cog_unload", None):
        return await discord.utils.maybe_coroutine(meth)


async def cog_before_invoke(self: DISCORD_COG_TYPE, context: PyLavContext):
    try:
        await self.pylav.wait_until_ready(timeout=30)
    except TimeoutError as e:
        LOGGER.debug("Discarded command due to PyLav not being ready within 30 seconds")

        LOGGER.verbose(
            "Discarded command due to PyLav not being ready within 30 seconds - Guild: %s - Command: %s",
            context.guild,
            context.command.qualified_name,
        )

        raise CheckFailure(_("PyLav is starting up; please try again in a few minutes.")) from e
    if meth := getattr(self, "__pylav_original_cog_before_invoke", None):
        return await discord.utils.maybe_coroutine(meth)


async def initialize(self: DISCORD_COG_TYPE, *args, **kwargs) -> None:
    if not self.init_called:
        await self.pylav.register(self)
        await self.pylav.initialize()
        self.init_called = True
    if meth := getattr(self, "__pylav_original_initialize", None):
        return await discord.utils.maybe_coroutine(meth, *args, **kwargs)


async def cog_check(self: DISCORD_COG_TYPE, context: PyLavContext) -> bool:
    # This cog mock discord objects and sends them on the listener
    #   Due to the potential risk for unexpected behaviour - disabled all commands if this cog is loaded.
    if any(context.bot.get_cog(name) is not None for name in INCOMPATIBLE_COGS):
        return False
    if not (getattr(context.bot, "pylav", None)):
        return False
    meth = getattr(self, "__pylav_original_cog_check", None)
    if not context.guild:
        return await discord.utils.maybe_coroutine(meth, context) if meth else True
    if getattr(context, "player", None):
        config = context.player.config
    else:
        config = context.bot.pylav.player_config_manager.get_config(context.guild.id)

    if (channel_id := await config.fetch_text_channel_id()) != 0 and channel_id != context.channel.id:
        return False
    return await discord.utils.maybe_coroutine(meth, context) if meth else True


def class_factory(
    bot: DISCORD_BOT_TYPE,
    cls: type[DISCORD_COG_TYPE],
    cogargs: tuple[object],
    cogkwargs: dict[str, object],
) -> DISCORD_COG_TYPE:  # sourcery no-metrics
    """
    Creates a new class which inherits from the given class and overrides the following methods:
    - cog_check
    - cog_unload
    - cog_before_invoke
    - initialize
    - cog_command_error
    """
    if not bot.get_command(pylav_credits.qualified_name):
        bot.add_command(pylav_credits)
    if not bot.get_command(pylav_version.qualified_name):
        bot.add_command(pylav_version)
    argspec = inspect.getfullargspec(cls.__init__)
    if ("bot" in argspec.args or "bot" in argspec.kwonlyargs) and bot not in cogargs:
        cogkwargs["bot"] = bot

    cog_instance = cls(*cogargs, **cogkwargs)
    if not hasattr(cog_instance, "__version__"):
        cog_instance.__version__ = "0.0.0"
    cog_instance.pylav = Client(bot=bot, cog=cog_instance, config_folder=cog_data_path(raw_name="PyLav"))
    cog_instance.bot = bot
    cog_instance.init_called = False
    cog_instance._init_task = cls.cog_check
    cog_instance.lavalink = cog_instance.pylav
    old_cog_on_command_error = cog_instance._get_overridden_method(cog_instance.cog_command_error)
    old_cog_unload = cog_instance._get_overridden_method(cog_instance.cog_unload)
    old_cog_before_invoke = cog_instance._get_overridden_method(cog_instance.cog_before_invoke)
    old_cog_check = cog_instance._get_overridden_method(cog_instance.cog_check)
    old_cog_initialize = getattr(cog_instance, "initialize", None)
    if old_cog_on_command_error:
        cog_instance.__pylav_original_cog_command_error = old_cog_on_command_error
    if old_cog_unload:
        cog_instance.__pylav_original_cog_unload = old_cog_unload
    if old_cog_before_invoke:
        cog_instance.__pylav_original_cog_before_invoke = old_cog_before_invoke
    if old_cog_check:
        cog_instance.__pylav_original_cog_check = old_cog_check
    if old_cog_initialize:
        cog_instance.__pylav_original_initialize = old_cog_initialize

    cog_instance.cog_command_error = MethodType(cog_command_error, cog_instance)
    cog_instance.cog_unload = MethodType(cog_unload, cog_instance)
    cog_instance.cog_before_invoke = MethodType(cog_before_invoke, cog_instance)
    cog_instance.initialize = MethodType(initialize, cog_instance)
    cog_instance.cog_check = MethodType(cog_check, cog_instance)

    return cog_instance


async def pylav_auto_setup(
    bot: DISCORD_BOT_TYPE,
    cog_cls: type[DISCORD_COG_TYPE],
    cogargs: tuple[object, ...] = None,
    cogkwargs: dict[str, object] = None,
    initargs: tuple[object, ...] = None,
    initkwargs: dict[str, object] = None,
) -> DISCORD_COG_TYPE:
    """Injects all the methods and attributes to respect PyLav Settings and keep the user experience consistent.

    Adds `.bot` attribute to the cog instance.
    Adds `.pylav` attribute to the cog instance and starts up PyLav
    Overwrites cog_unload method to unregister the cog from Lavalink, calling the original cog_unload method once the PyLav unregister code is run.
    Overwrites cog_before_invoke To force commands to wait for PyLav to be ready
    Overwrites cog_check method to check if the cog is allowed to run in the current context. If called within a Guild then we check if we can run as per the PyLav Command channel lock, if this check passes then the original cog_check method is called.
    Overwrites cog_command_error method to handle PyLav errors raised by the cog, if the cog defines their own cog_command_error method, this will still be called after the built-in PyLav error handling if the error raised was unhandled.
    Overwrites initialize method to handle PyLav startup, calling the original initialize method once the PyLav initialization code is run, if such method exists. code is run.

    Args:
        bot (DISCORD_BOT_TYPE): The bot instance to load the cog instance to.
        cog_cls (type[DISCORD_COG_TYPE]): The cog class load.
        cogargs (tuple[object]): The arguments to pass to the cog class.
        cogkwargs (dict[str, object]): The keyword arguments to pass to the cog class.
        initargs (tuple[object]): The arguments to pass to the initialize method.
        initkwargs (dict[str, object]): The keyword arguments to pass to the initialize method.

    Returns:
        DISCORD_COG_TYPE: The cog instance loaded to the bot.

    Example:
        >>> from pylav.extension.red.utils.required_methods import pylav_auto_setup
        >>> from discord.ext.commands import Cog
        >>> class MyCogClass(Cog):
        ...     def __init__(self, bot: DISCORD_BOT_TYPE, special_arg: object):
        ...         self.bot = bot
        ...         self.special_arg = special_arg


        >>> async def setup(bot: DISCORD_BOT_TYPE) -> None:
        ...     await pylav_auto_setup(bot, MyCogClass, cogargs=(), cogkwargs=dict(special_arg=42), initargs=(),
        initkwargs=dict())

    """
    if any(bot.get_cog(name) is not None for name in INCOMPATIBLE_COGS if (_name := name)):
        raise IncompatibleException(
            f"{_name} is loaded, this cog is incompatible with PyLav - PyLav will not work as long as this cog is loaded"
        )
    if cogargs is None:
        cogargs = ()
    if cogkwargs is None:
        cogkwargs = {}
    if initargs is None:
        initargs = ()
    if initkwargs is None:
        initkwargs = {}
    async with _LOCK:
        cog_instance = class_factory(bot, cog_cls, cogargs, cogkwargs)
        await bot.add_cog(cog_instance)
    cog_instance._init_task = asyncio.create_task(cog_instance.initialize(*initargs, **initkwargs))
    cog_instance._init_task.add_done_callback(_done_callback)
    return cog_instance
