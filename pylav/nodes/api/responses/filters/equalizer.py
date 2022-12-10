from __future__ import annotations

import dataclasses
from typing import Annotated, Union

from pylav.nodes.api.responses.filters.misc import ValueRange


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class EqualizerBand:
    band: Annotated[int | None, ValueRange(min=0, max=14)]
    gain: Annotated[float | None, ValueRange(min=-0.25, max=1.0)]

    def to_dict(self) -> dict[str, float | int]:
        response: dict[str, float | int] = {}
        if self.band is not None:
            response["band"] = self.band
        if self.gain is not None:
            response["gain"] = self.gain
        return response


Equalizer = list[Union[EqualizerBand, dict]]
