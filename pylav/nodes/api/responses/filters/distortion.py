from __future__ import annotations

import dataclasses


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Distortion:
    sinOffset: float | None = None
    sinScale: float | None = None
    cosOffset: float | None = None
    cosScale: float | None = None
    tanOffset: float | None = None
    tanScale: float | None = None
    offset: float | None = None
    scale: float | None = None

    def to_dict(self) -> dict[str, float]:
        response = {}
        if self.sinOffset is not None:
            response["sinOffset"] = self.sinOffset
        if self.sinScale is not None:
            response["sinScale"] = self.sinScale
        if self.cosOffset is not None:
            response["cosOffset"] = self.cosOffset
        if self.cosScale is not None:
            response["cosScale"] = self.cosScale
        if self.tanOffset is not None:
            response["tanOffset"] = self.tanOffset
        if self.tanScale is not None:
            response["tanScale"] = self.tanScale
        if self.offset is not None:
            response["offset"] = self.offset
        if self.scale is not None:
            response["scale"] = self.scale
        return response
