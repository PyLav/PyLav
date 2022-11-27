from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")

SourcesT = TypeVar("SourcesT", bound="Union[menus.ListPageSource]")
GenericT = TypeVar("GenericT")
