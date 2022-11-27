from __future__ import annotations

from typing import TypeVar, Union

from redbot.vendored.discord.ext import menus

T = TypeVar("T")

SourcesT = TypeVar("SourcesT", bound="Union[menus.ListPageSource]")
GenericT = TypeVar("GenericT")
