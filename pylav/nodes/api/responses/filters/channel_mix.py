from __future__ import annotations

import dataclasses
from typing import Annotated

from pylav.nodes.api.responses.filters.misc import ValueRange


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class ChannelMix:
    leftToLeft: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    leftToRight: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    rightToLeft: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None
    rightToRight: Annotated[float | None, ValueRange(min=0.0, max=1.0)] = None

    def to_dict(self) -> dict[str, float]:
        response = {}
        if self.leftToLeft is not None:
            response["leftToLeft"] = self.leftToLeft
        if self.leftToRight is not None:
            response["leftToRight"] = self.leftToRight
        if self.rightToLeft is not None:
            response["rightToLeft"] = self.rightToLeft
        if self.rightToRight is not None:
            response["rightToRight"] = self.rightToRight
        return response
