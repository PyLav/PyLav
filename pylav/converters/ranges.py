from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, TypeVar, Union

from discord import AppCommandOptionType
from discord.app_commands import Choice, Transformer
from discord.app_commands.transformers import _TransformMetadata
from discord.ext import commands

from pylav.types import ContextT, InteractionT

if TYPE_CHECKING:

    RangeConverter = TypeVar("RangeConverter", bound=Union[int, float])
else:

    class RangeConverter(Transformer):
        def __class_getitem__(cls, obj) -> _TransformMetadata:
            if not isinstance(obj, tuple):
                raise TypeError(f"expected tuple for arguments, received {obj.__class__!r} instead")

            if len(obj) == 2:
                obj = (*obj, None)
            elif len(obj) != 3:
                raise TypeError("Range accepts either two or three arguments with the first being the type of range.")

            obj_type, min, max = obj

            if min is None and max is None:
                raise TypeError("Range must not be empty")

            if min is not None and max is not None and not isinstance(min, type(max)):
                raise TypeError("Both min and max in Range must be the same type")
            if obj_type is int:
                opt_type = AppCommandOptionType.integer
            else:
                raise TypeError(f"expected int as range type, received {obj_type!r} instead")
            ns = {
                "type": classmethod(lambda _: opt_type),
                "min_value": classmethod(lambda _: min),
                "max_value": classmethod(lambda _: max),
            }

            transformer = type(f"RangeTransformerT{uuid.uuid4().hex[:6].upper()}", (RangeConverter,), ns)
            return _TransformMetadata(transformer)

        @classmethod
        async def convert(cls, ctx: ContextT, arg: str) -> int:
            """Converts a node name or ID to a list of matching objects."""
            try:
                level = int(arg)
            except ValueError as e:
                raise commands.BadArgument("Invalid input, argument must be an integer i.e 1, 2, 3, 4, 5") from e

            if (cls.min_value() is not None and level < cls.min_value()) or (
                cls.max_value() is not None and level > cls.max_value()
            ):
                if cls.min_value() is not None and cls.max_value() is not None:
                    raise commands.BadArgument(f"Argument must be between {cls.min_value()} and {cls.max_value()}.")
                elif cls.min_value() is not None:
                    raise commands.BadArgument(f"Argument must be at least {cls.min_value()}.")
                else:
                    raise commands.BadArgument(f"Argument must be at most {cls.max_value()}.")
            return level

        @classmethod
        async def transform(cls, interaction: InteractionT, argument: str) -> int:
            ctx = await interaction.client.get_context(interaction)
            return await cls.convert(ctx, argument)

        async def autocomplete(self, interaction: InteractionT, current: str) -> list[Choice]:
            return []
