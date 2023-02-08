from __future__ import annotations

import collections
from typing import Any, Final

from deepdiff import DeepDiff  # type: ignore

from pylav.players.filters.misc import FilterMixin

_SUPPORTED_BANDS: Final = 15  # 1 Indexed


class Equalizer(FilterMixin):
    """Class representing a usable equalizer.

    Parameters
    ------------
    levels: List[Tuple[int, float]]
        A list of tuple pairs containing a band int and gain float.
    name: str
        An Optional string to name this Equalizer. Defaults to 'CustomEqualizer'
    """

    __slots__ = ("_eq", "_name", "_default")

    def __init__(self, *, levels: list[dict[str, int | float | None]], name: str = "CustomEqualizer") -> None:
        super().__init__()
        self._eq = self._factory(levels)
        self._name = name

    def to_dict(self) -> dict[str, list[dict[str, int | float | None]] | str | bool]:
        """Returns a dictionary representation of the Equalizer"""
        return {"equalizer": self._eq, "name": self._name}

    @classmethod
    def from_dict(cls, data: dict[str, list[dict[str, int | float | None]] | str | bool]) -> Equalizer:
        """Creates an Equalizer from a dictionary"""
        return cls(levels=data["equalizer"], name=data["name"])

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"<Equalizer: name={self._name}, eq={self._eq}>"

    @property
    def index(self) -> dict[int, float]:
        d: dict[Any, float] = collections.defaultdict(float)
        d |= {d["band"]: d["gain"] for d in self._eq}
        return d

    def __eq__(self, other: Any) -> bool:
        """Overrides the default implementation"""
        if isinstance(other, Equalizer):
            return bool(
                DeepDiff(
                    self._eq, other._eq, ignore_order=True, max_passes=1, cache_size=100, exclude_paths=["root['name']"]
                )
            )
        return NotImplemented

    @property
    def name(self) -> str:
        """The Equalizers friendly name"""
        return self._name

    @staticmethod
    def _factory(levels: list[dict[str, int | float]]) -> list[dict[str, int | float]]:
        if not levels:
            return []
        if not isinstance(levels[0], dict):
            raise TypeError("Equalizer levels should be a list of dictionaries")

        _dict: dict[str, float] = collections.defaultdict(float)
        for level in levels:
            _dict[str(level["band"])] = level["gain"]
        return [{"band": i, "gain": _dict[str(i)]} for i in range(_SUPPORTED_BANDS) if _dict[str(i)]]

    @classmethod
    def build(cls, *, levels: list[dict[str, int | float]], name: str = "CustomEqualizer") -> Equalizer:
        """Build a custom Equalizer class with the provided levels.

        Parameters
        ------------
        levels: list[dict[str, int | float]]
            A list of dictionaries containing the band and gain for each band.
        name: str
            An Optional string to name this Equalizer. Defaults to 'CustomEqualizer'
        """
        return cls(levels=levels, name=name)

    @classmethod
    def flat(cls) -> Equalizer:
        """Flat Equalizer.
        Resets your EQ to Flat.
        """
        return cls(
            levels=[],
            name="Default",
        )

    @classmethod
    def default(cls) -> Equalizer:
        return cls.flat()

    def get(self) -> list[dict[str, int | float]]:
        return [] if self.off else self._eq

    def reset(self) -> None:
        eq = Equalizer.flat()
        self._eq = eq._eq
        self._name = eq._name

    def set_gain(self, band: int, gain: float) -> None:
        if band < 0 or band >= _SUPPORTED_BANDS:
            raise IndexError(f"Band {band} does not exist!")

        band = next((index for (index, d) in enumerate(self._eq) if d["band"] == band), -1)
        if band == -1:
            raise IndexError(f"Band {band} does not exist!")

        gain = float(min(max(gain, -0.25), 1.0))
        self._eq[band]["gain"] = gain
        if gain == 0.0:
            # Discard any redundant 0.0 gains
            self._eq[band].pop("gain", 0.0)

    def get_gain(self, band: int) -> float:
        if band < 0 or band >= _SUPPORTED_BANDS:
            raise IndexError(f"Band {band} does not exist!")
        return self.index[band]

    def visualise(self) -> str:
        block = ""
        bands = [str(band + 1).zfill(2) for band in range(_SUPPORTED_BANDS)]
        bottom = (" " * 8) + " ".join(bands)
        gains = [x * 0.01 for x in range(-25, 105, 5)]
        gains.reverse()

        for gain in gains:
            prefix = ""
            if gain > 0:
                prefix = "+"
            elif gain == 0:
                prefix = " "

            block += f"{prefix}{gain:.2f} | "

            for value in self._eq:
                cur_gain = value.get("gain", 0.0)
                block += "[] " if cur_gain >= gain else "   "
            block += "\n"

        block += bottom
        return block
