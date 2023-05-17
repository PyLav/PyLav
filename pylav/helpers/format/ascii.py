from __future__ import annotations

from math import sqrt

from pylav.constants.misc import ASCII_COLOURS
from pylav.type_hints.generics import SupportsStr


class _BackgroundColourCodes:
    """Background colour codes for ANSI escape sequences."""

    dark_blue = "40"
    orange = "41"
    blue = "42"
    turquoise = "43"
    gray = "44"
    indigo = "45"
    light_gray = "46"
    white = "47"


class EightBitANSI:
    """Eight-bit ANSI escape sequences."""

    escape = "\u001b["

    black = "30"
    red = "31"
    green = "32"
    yellow = "33"
    blue = "34"
    magenta = "35"
    cyan = "36"
    white = "37"

    normal = reset = "0"
    bold = "1"
    italic = "3"
    underline = "4"
    default = "39"
    background = _BackgroundColourCodes

    @classmethod
    def colorize(
        cls,
        text: SupportsStr,
        color: str,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Colorize a string with ANSI escape sequences."""
        colour = [getattr(cls, color, "39")]
        if background and (background := getattr(cls.background, background, None)):
            colour.append(background)
        if bold:
            colour.append(cls.bold)
        if italic:
            colour.append(cls.italic)
        if underline:
            colour.append(cls.underline)

        colour_code = f"{cls.escape}{';'.join(colour)}m"
        colour_reset = f"{cls.escape}{cls.reset}m"
        text = f"{text}".replace("\n", f"{colour_reset}\n{colour_code}")

        return f"{colour_code}{text}{colour_reset}"

    @classmethod
    def paint_black(
        cls,
        text: SupportsStr,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string black."""
        return cls.colorize(text, "black", bold, underline, background, italic)

    @classmethod
    def paint_red(
        cls,
        text: SupportsStr,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string red."""
        return cls.colorize(text, "red", bold, underline, background, italic)

    @classmethod
    def paint_green(
        cls,
        text: SupportsStr,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string green."""
        return cls.colorize(text, "green", bold, underline, background, italic)

    @classmethod
    def paint_yellow(
        cls,
        text: SupportsStr,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string yellow."""
        return cls.colorize(text, "yellow", bold, underline, background, italic)

    @classmethod
    def paint_blue(
        cls,
        text: SupportsStr,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string blue."""
        return cls.colorize(text, "blue", bold, underline, background, italic)

    @classmethod
    def paint_magenta(
        cls,
        text: SupportsStr,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string magenta."""
        return cls.colorize(text, "magenta", bold, underline, background, italic)

    @classmethod
    def paint_cyan(
        cls,
        text: SupportsStr,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string cyan."""
        return cls.colorize(text, "cyan", bold, underline, background, italic)

    @classmethod
    def paint_white(
        cls,
        text: SupportsStr,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string white."""
        return cls.colorize(text, "white", bold, underline, background, italic)

    @classmethod
    def closest_from_rgb(cls, r: int, g: int, b: int) -> str:
        """Get the closest 4-bit ANSI colour from a given RGB value."""
        return cls.closest_color(r, g, b)

    @classmethod
    def closest_from_hex(cls, value: str) -> str:
        """Get the closest 4-bit ANSI colour from a given hex value."""
        value = value.lstrip("#")
        lv = len(value)
        return cls.closest_color(*tuple(int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3)))

    @classmethod
    def closest_color(cls, red: int, green: int, blue: int) -> str:
        """Get the closest 4-bit ANSI colour from a given RGB value."""
        color_diffs = []
        for name, color in ASCII_COLOURS.items():
            cr, cg, cb = color
            color_diff = sqrt((red - cr) ** 2 + (green - cg) ** 2 + (blue - cb) ** 2)
            color_diffs.append((color_diff, name))
        return min(color_diffs)[1]
