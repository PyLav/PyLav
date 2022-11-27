from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from discord.app_commands import Choice, Transformer
from discord.ext import commands
from redbot.core.i18n import Translator

from pylav.exceptions import EntryNotFoundError
from pylav.types import InteractionT
from pylav.utils import PyLavContext

_ = Translator("PyLavShared", Path(__file__))

if TYPE_CHECKING:
    BassBoostConverter = str
else:

    class BassBoostConverter(Transformer):
        @classmethod
        async def convert(cls, ctx: PyLavContext, arg: str) -> str:
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
                    raise EntryNotFoundError
            except EntryNotFoundError as e:
                raise commands.BadArgument(_("Bass boost with name `{arg}` not found").format(arg=arg)) from e

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> str:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        @classmethod
        async def autocomplete(cls, interaction: InteractionT, current: str) -> list[Choice]:
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
                    ("Off", _("Off")),
                ]
                if current.lower() in p.lower()
            ]
