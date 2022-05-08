from __future__ import annotations

from pylav.filters.utils import FilterMixin


class Distortion(FilterMixin):
    def __init__(
        self,
        sin_offset: float,
        sin_scale: float,
        cos_offset: float,
        cos_scale: float,
        tan_offset: float,
        tan_scale: float,
        offset: float,
        scale: float,
    ):
        self.sin_offset = sin_offset
        self.sin_scale = sin_scale
        self.cos_offset = cos_offset
        self.cos_scale = cos_scale
        self.tan_offset = tan_offset
        self.tan_scale = tan_scale
        self.offset = offset
        self.scale = scale
        self.off = False

    def to_dict(self) -> dict:
        return {
            "sin_offset": self.sin_offset,
            "sin_scale": self.sin_scale,
            "cos_offset": self.cos_offset,
            "cos_scale": self.cos_scale,
            "tan_offset": self.tan_offset,
            "tan_scale": self.tan_scale,
            "offset": self.offset,
            "scale": self.scale,
            "off": self.off,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Distortion:
        c = cls(
            sin_offset=data["sin_offset"],
            sin_scale=data["sin_scale"],
            cos_offset=data["cos_offset"],
            cos_scale=data["cos_scale"],
            tan_offset=data["tan_offset"],
            tan_scale=data["tan_scale"],
            offset=data["offset"],
            scale=data["scale"],
        )
        c.off = data["off"]
        return c

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
    def sin_offset(self) -> float:
        return self._sin_offset

    @sin_offset.setter
    def sin_offset(self, v: float):
        self._sin_offset = v
        self.off = False

    @property
    def sin_scale(self) -> float:
        return self._sin_scale

    @sin_scale.setter
    def sin_scale(self, v: float):
        self._sin_scale = v

    @property
    def cos_offset(self) -> float:
        return self._cos_offset

    @cos_offset.setter
    def cos_offset(self, v: float):
        self._cos_offset = v
        self.off = False

    @property
    def cos_scale(self) -> float:
        return self._cos_scale

    @cos_scale.setter
    def cos_scale(self, v: float):
        self._cos_scale = v
        self.off = False

    @property
    def tan_offset(self) -> float:
        return self._tan_offset

    @tan_offset.setter
    def tan_offset(self, v: float):
        self._tan_offset = v
        self.off = False

    @property
    def tan_scale(self) -> float:
        return self._tan_scale

    @tan_scale.setter
    def tan_scale(self, v: float):
        self._tan_scale = v
        self.off = False

    @property
    def offset(self) -> float:
        return self._offset

    @offset.setter
    def offset(self, v: float):
        self._offset = v
        self.off = False

    @property
    def scale(self) -> float:
        return self._scale

    @scale.setter
    def scale(self, v: float):
        self._scale = v
        self.off = False

    @classmethod
    def default(cls) -> Distortion:
        c = cls(
            sin_offset=0.0,
            sin_scale=1.0,
            cos_offset=0.0,
            cos_scale=1.0,
            tan_offset=0.0,
            tan_scale=1.0,
            offset=0.0,
            scale=1.0,
        )
        c.off = True
        return c

    def get(self) -> dict[str, float]:
        if self.off:
            return {}
        return {
            "sinOffset": self.sin_offset,
            "sinScale": self.sin_scale,
            "cosOffset": self.cos_offset,
            "cosScale": self.cos_scale,
            "tanOffset": self.tan_offset,
            "tanScale": self.tan_scale,
            "offset": self.offset,
            "scale": self.scale,
        }

    def reset(self) -> None:
        self.sin_offset = 0.0
        self.sin_scale = 1.0
        self.cos_offset = 0.0
        self.cos_scale = 1.0
        self.tan_offset = 0.0
        self.tan_scale = 1.0
        self.offset = 0.0
        self.scale = 1.0
        self.off = True
