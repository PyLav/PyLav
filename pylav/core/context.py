from __future__ import annotations

import contextlib
import datetime
import pathlib
from collections.abc import Iterable
from copy import copy
from typing import TYPE_CHECKING, Any

import discord
from discord import Attachment, Message, MessageType, PartialMessageable
from discord.ext import commands as dpy_command
from discord.ext.commands import Context as DpyContext
from discord.ext.commands.view import StringView
from discord.types.embed import EmbedType
from discord.utils import MISSING as D_MISSING  # noqa

from pylav.type_hints.bot import DISCORD_BOT_TYPE, DISCORD_COG_TYPE, DISCORD_CONTEXT_TYPE, DISCORD_INTERACTION_TYPE
from pylav.utils.vendor.redbot import MessagePredicate

try:
    from redbot.core.commands import Command
    from redbot.core.commands import Context as OriginalContextClass
except ImportError:
    from discord.ext.commands import Command
    from discord.ext.commands import Context as OriginalContextClass


try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLav", pathlib.Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


if TYPE_CHECKING:
    from pylav.players.player import Player


class PyLavContext(OriginalContextClass):
    _original_ctx_or_interaction: DISCORD_CONTEXT_TYPE | DISCORD_INTERACTION_TYPE | None
    bot: DISCORD_BOT_TYPE
    client: DISCORD_BOT_TYPE
    interaction: DISCORD_INTERACTION_TYPE | None

    def __init__(
        self,
        *,
        message: Message,
        bot: DISCORD_BOT_TYPE,
        view: StringView,
        args: list[Any] = D_MISSING,
        kwargs: dict[str, Any] = D_MISSING,
        prefix: str | None = None,
        command: Command[Any, ..., Any] | None = None,
        invoked_with: str | None = None,
        invoked_parents: list[str] = D_MISSING,
        invoked_subcommand: Command[Any, ..., Any] | None = None,  # noqa
        subcommand_passed: str | None = None,
        command_failed: bool = False,
        current_parameter: discord.ext.commands.Parameter | None = None,
        current_argument: str | None = None,
        interaction: DISCORD_INTERACTION_TYPE | None = None,
    ):
        super().__init__(
            message=message,
            bot=bot,
            view=view,
            args=args,
            kwargs=kwargs,
            prefix=prefix,
            command=command,
            invoked_with=invoked_with,
            invoked_parents=invoked_parents,
            invoked_subcommand=invoked_subcommand,
            subcommand_passed=subcommand_passed,
            command_failed=command_failed,
            current_parameter=current_parameter,
            current_argument=current_argument,
            interaction=interaction,
        )

        self._original_ctx_or_interaction = None
        self.lavalink = bot.pylav
        self.pylav = bot.pylav

    @discord.utils.cached_property
    def author(self) -> discord.User | discord.Member:
        """Union[:class:`~discord.User`, :class:`.Member`]:
        Returns the author associated with this context's command. Shorthand for :attr:`.Message.author`
        """
        # When using client.get_context() on a button interaction the "author" becomes the bot user
        #   This ensures the original author remains the author of the context
        if isinstance(self._original_ctx_or_interaction, discord.Interaction):
            return self._original_ctx_or_interaction.user
        elif isinstance(self._original_ctx_or_interaction, DpyContext):
            return self._original_ctx_or_interaction.author
        else:
            return self.message.author

    @property
    def cog(self) -> DISCORD_COG_TYPE | None:
        """Optional[:class:`.Cog`]: Returns the cog associated with this context's command. None if it does not
        exist"""

        return None if self.command is None else self.command.cog

    @discord.utils.cached_property
    def guild(self) -> discord.Guild | None:
        """Optional[:class:`.Guild`]: Returns the guild associated with this context's command. None if not
        available"""
        return getattr(self.author, "guild", None)

    @discord.utils.cached_property
    def channel(self) -> discord.abc.MessageableChannel:
        """Union[:class:`.abc.Messageable`]: Returns the channel associated with this context's command.
        Shorthand for :attr:`.Message.channel`.
        """
        if isinstance(self._original_ctx_or_interaction, (discord.Interaction, DpyContext)):
            return self._original_ctx_or_interaction.channel  # type: ignore
        else:
            return self.message.channel

    @property
    def player(self) -> Player | None:
        """
        Get player
        """
        return self.pylav.get_player(self.guild)

    async def connect_player(
        self, channel: discord.channel.VocalGuildChannel = None, self_deaf: bool | None = None
    ) -> Player:
        """
        Connect player
        """
        requester = self.author
        channel = channel or self.author.voice.channel
        return await self.pylav.connect_player(requester=requester, channel=channel, self_deaf=self_deaf)

    @property
    def original_ctx_or_interaction(self) -> DISCORD_CONTEXT_TYPE | DISCORD_INTERACTION_TYPE | None:
        """
        Get original ctx or interaction
        """
        return self._original_ctx_or_interaction

    async def construct_embed(
        self,
        *,
        embed: discord.Embed = None,
        colour: discord.Colour | int | None = None,
        color: discord.Colour | int | None = None,
        title: str = None,
        embed_type: EmbedType = "rich",
        url: str = None,
        description: str = None,
        timestamp: datetime.datetime = None,
        author_name: str = None,
        author_url: str = None,
        thumbnail: str = None,
        footer: str = None,
        footer_url: str = None,
        messageable: discord.abc.Messageable | DISCORD_INTERACTION_TYPE = None,
    ) -> discord.Embed:
        """
        Construct embed
        """
        return await self.pylav.construct_embed(
            embed=embed,
            colour=colour,
            color=color,
            title=title,
            embed_type=embed_type,
            url=url,
            description=description,
            timestamp=timestamp,
            author_name=author_name,
            author_url=author_url,
            thumbnail=thumbnail,
            footer=footer,
            footer_url=footer_url,
            messageable=messageable or self,
        )

    @classmethod
    async def from_interaction(cls, interaction: DISCORD_INTERACTION_TYPE, /) -> PyLavContext:
        #  When using this on a button interaction it raises an error as expected.
        #   This makes the `get_context` method work with buttons by storing the original context

        added_dummy = False
        if isinstance(interaction, discord.Interaction) and interaction.command is None:
            setattr(interaction, "_cs_command", _dummy_command)
            added_dummy = True

        # Circular import
        from discord.ext.commands.bot import BotBase

        if not isinstance(interaction.client, BotBase):
            raise TypeError("Interaction client is not derived from commands.Bot or commands.AutoShardedBot")

        command = interaction.command
        if command is None:
            raise ValueError("interaction does not have command data")

        bot: DISCORD_BOT_TYPE = interaction.client  # type: ignore
        data = interaction.data  # type: ignore
        if interaction.message is None:
            synthetic_payload = {
                "id": interaction.id,
                "reactions": [],
                "embeds": [],
                "mention_everyone": False,
                "tts": False,
                "pinned": False,
                "edited_timestamp": None,
                "type": MessageType.chat_input_command
                if data.get("type", 1) == 1
                else MessageType.context_menu_command,
                "flags": 64,
                "content": "",
                "mentions": [],
                "mention_roles": [],
                "attachments": [],
            }

            if interaction.channel_id is None:
                raise RuntimeError("interaction channel ID is null, this is probably a Discord bug")

            channel = interaction.channel or PartialMessageable(
                state=interaction._state, guild_id=interaction.guild_id, id=interaction.channel_id
            )
            message = Message(state=interaction._state, channel=channel, data=synthetic_payload)  # type: ignore
            message.author = interaction.user
            message.attachments = [a for _, a in interaction.namespace if isinstance(a, Attachment)]
        else:
            message = interaction.message

        prefix = "/" if data.get("type", 1) == 1 else "\u200b"  # Mock the prefix
        ctx = cls(
            message=message,
            bot=bot,
            view=StringView(""),
            args=[],
            kwargs={},
            prefix=prefix,
            interaction=interaction,
            invoked_with=command.name,
            command=command,  # type: ignore # this will be a hybrid command, technically
        )
        interaction._baton = ctx
        ctx.command_failed = interaction.command_failed
        if added_dummy:
            ctx.command = None
        ctx._original_ctx_or_interaction = interaction
        return ctx

    def dispatch_command(
        self, message: discord.Message, command: Command, author: discord.abc.User, args: list[str], prefix: str = None
    ) -> None:
        """
        Dispatch command
        """
        command_str = f"{prefix}{command.qualified_name} {' '.join(args)}"
        msg = copy(message)
        msg.author = author
        msg.content = command_str
        self.bot.dispatch("message", msg)

    async def send_interactive(
        self, messages: Iterable[str], box_lang: str = None, timeout: int = 15, embed: bool = False
    ) -> list[discord.Message]:
        """Send multiple messages interactively.

        The user will be prompted for whether or not they would like to view
        the next message, one at a time. They will also be notified of how
        many messages are remaining on each prompt.

        Parameters
        ----------
        messages : `iterable` of `str`
            The messages to send.
        box_lang : str
            If specified, each message will be contained within a codeblock of
            this language.
        timeout : int
            How long the user has to respond to the prompt before it times out.
            After timing out, the bot deletes its prompt message.
        embed : bool
            Whether or not to send the messages as embeds.

        """
        messages = tuple(messages)
        ret = []

        for idx, page in enumerate(messages, 1):
            if box_lang is None:
                msg = (
                    await self.send(embed=await self.pylav.construct_embed(description=page, messageable=self))
                    if embed
                    else await self.send(page)
                )
            elif embed:
                msg = await self.send(
                    embed=await self.pylav.construct_embed(description=f"```{box_lang}\n{page}\n```", messageable=self)
                )
            else:
                msg = await self.send(f"```{box_lang}\n{page}\n```")
            ret.append(msg)
            n_remaining = len(messages) - idx
            if n_remaining > 0:
                match n_remaining:
                    case 1:
                        message = _("There is still 1 message remaining. Type `more` to continue.")
                    case __:
                        message = _(
                            "There are still {remaining_variable_do_not_translate} messages remaining. Type `more` to continue."
                        ).format(remaining_variable_do_not_translate=n_remaining)

                query = await self.send(message)

                try:
                    resp = await self.bot.wait_for(
                        "message",
                        check=MessagePredicate.lower_equal_to("more", self),
                        timeout=timeout,
                    )
                except TimeoutError:
                    with contextlib.suppress(discord.HTTPException):
                        await query.delete()
                    break
                else:
                    try:
                        await self.channel.delete_messages((query, resp))
                    except (discord.HTTPException, AttributeError):
                        # In case the bot can't delete other users' messages,
                        # or is not a bot account
                        # or channel is a DM
                        with contextlib.suppress(discord.HTTPException):
                            await query.delete()
        return ret


@dpy_command.command(name="__dummy_command", hidden=True, disabled=True)
async def _dummy_command(self, context: PyLavContext) -> None:  # noqa
    """Does nothing"""
