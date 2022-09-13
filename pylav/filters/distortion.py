from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Distortion(FilterMixin):
    __slots__ = (
        "_sin_offset",
        "_sin_scale",
        "_cos_offset",
        "_cos_scale",
        "_tan_offset",
        "_tan_scale",
        "_offset",
        "_scale",
        "_default",
    )

    def __init__(
        self,
        sin_offset: float = None,
        sin_scale: float = None,
        cos_offset: float = None,
        cos_scale: float = None,
        tan_offset: float = None,
        tan_scale: float = None,
        offset: float = None,
        scale: float = None,
    ):
        super().__init__()
        self.sin_offset = sin_offset
        self.sin_scale = sin_scale
        self.cos_offset = cos_offset
        self.cos_scale = cos_scale
        self.tan_offset = tan_offset
        self.tan_scale = tan_scale
        self.offset = offset
        self.scale = scale

    def to_dict(self) -> dict[str, float | bool | None]:
        return {
            "sin_offset": self.sin_offset,
            "sin_scale": self.sin_scale,
            "cos_offset": self.cos_offset,
            "cos_scale": self.cos_scale,
            "tan_offset": self.tan_offset,
            "tan_scale": self.tan_scale,
            "offset": self.offset,
            "scale": self.scale,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | bool | None]) -> Distortion:
        return cls(
            sin_offset=data["sin_offset"],
            sin_scale=data["sin_scale"],
            cos_offset=data["cos_offset"],
            cos_scale=data["cos_scale"],
            tan_offset=data["tan_offset"],
            tan_scale=data["tan_scale"],
            offset=data["offset"],
            scale=data["scale"],
        )

    def __repr__(self):
        return (
            "<Distortion: "
            f"sin_offset={self.sin_offset}, "
            f"sin_scale={self.sin_scale}, "
            f"cos_offset={self.cos_offset}, "
            f"cos_scale={self.cos_scale}, "
            f"tan_offset={self.tan_offset}, "
            f"tan_scale={self.tan_scale}, "
            f"offset={self.offset}, "
            f"scale={self.scale}>"
        )

    @property
    def sin_offset(self) -> float | None:
        return self._sin_offset

    @sin_offset.setter
    def sin_offset(self, v: float | None) -> None:
        self._sin_offset = v

    @property
    def sin_scale(self) -> float | None:
        return self._sin_scale

    @sin_scale.setter
    def sin_scale(self, v: float | None) -> None:
        self._sin_scale = v

    @property
    def cos_offset(self) -> float | None:
        return self._cos_offset

    @cos_offset.setter
    def cos_offset(self, v: float | None) -> None:
        self._cos_offset = v

    @property
    def cos_scale(self) -> float | None:
        return self._cos_scale

    @cos_scale.setter
    def cos_scale(self, v: float | None) -> None:
        self._cos_scale = v

    @property
    def tan_offset(self) -> float | None:
        return self._tan_offset

    @tan_offset.setter
    def tan_offset(self, v: float | None) -> None:
        self._tan_offset = v

    @property
    def tan_scale(self) -> float | None:
        return self._tan_scale

    @tan_scale.setter
    def tan_scale(self, v: float | None) -> None:
        self._tan_scale = v

    @property
    def offset(self) -> float | None:
        return self._offset

    @offset.setter
    def offset(self, v: float | None) -> None:
        self._offset = v

    @property
    def scale(self) -> float | None:
        return self._scale

    @scale.setter
    def scale(self, v: float | None) -> None:
        self._scale = v

    @classmethod
    def default(cls) -> Distortion:
        return cls()

    def get(self) -> dict[str, float]:
        if self.off:
            return {}
        response = {}
        if self.sin_offset is not None:
            response["sinOffset"] = self.sin_offset
        if self.sin_scale is not None:
            response["sinScale"] = self.sin_scale
        if self.cos_offset is not None:
            response["cosOffset"] = self.cos_offset
        if self.cos_scale is not None:
            response["cosScale"] = self.cos_scale
        if self.tan_offset is not None:
            response["tanOffset"] = self.tan_offset
        if self.tan_scale is not None:
            response["tanScale"] = self.tan_scale
        if self.offset is not None:
            response["offset"] = self.offset
        if self.scale is not None:
            response["scale"] = self.scale
        return response

    def reset(self) -> None:
        self.sin_scale = (
            self.cos_offset
        ) = self.cos_scale = self.tan_offset = self.tan_scale = self.offset = self.scale = self.sin_offset = None
