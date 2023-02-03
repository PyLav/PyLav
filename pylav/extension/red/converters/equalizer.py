from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from discord.app_commands import Choice, Transformer
from discord.ext import commands
from redbot.core.i18n import Translator

from pylav.core.context import PyLavContext
from pylav.exceptions.database import EntryNotFoundException
from pylav.type_hints.bot import DISCORD_INTERACTION_TYPE

_ = Translator("PyLav", Path(__file__))

if TYPE_CHECKING:
    BassBoostConverter = str
else:

    class BassBoostConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: PyLavContext, arg: str) -> str:  # noqa
            """Converts user input to a valid argument for the bassboost command"""

            try:
                if match := next(
                    filter(
                        lambda x: x.lower().startswith(arg.lower()),
                        [
                            "Maximum",
                            "Insane",
                            "Extreme",
                            "High",
                            "Very High",
                            "Medium",
                            "Fine Tuned",
                            "Cut-off",
                            "Off",
                        ],
                    ),
                    None,
                ):
                    return match
                else:
                    raise EntryNotFoundException
            except EntryNotFoundException as e:
                raise commands.BadArgument(
                    _(
                        "A bass boost profile with the name `{user_input_variable_do_not_translate}` was not found."
                    ).format(user_input_variable_do_not_translate=arg)
                ) from e

        @classmethod
        async def transform(cls, interaction: DISCORD_INTERACTION_TYPE, argument: str) -> str:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: DISCORD_INTERACTION_TYPE, current: str) -> list[Choice]:
            return [
                Choice(name=t, value=p)
                for p, t in [
                    ("Maximum", _("Maximum")),
                    ("Insane", _("Insane")),
                    ("Extreme", _("Extreme")),
                    ("Very High", _("Very High")),
                    ("High", _("High")),
                    ("Medium", _("Medium")),
                    ("Fine Tuned", _("Fine Tuned")),
                    ("Cut-off", _("Cut-off")),
                    ("Off", _("Turn off")),
                ]
                if current.lower() in p.lower()
            ]
