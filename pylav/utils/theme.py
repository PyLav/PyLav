from __future__ import annotations

from math import sqrt
from typing import Any

COLOURS = {
    "black": (1, 1, 1),
    "red": (220, 50, 47),
    "green": (133, 153, 0),
    "yellow": (181, 137, 0),
    "blue": (38, 139, 210),
    "magenta": (211, 54, 130),
    "cyan": (42, 161, 152),
    "white": (255, 255, 255),
}


class EightBitANSI:
    escape = "\u001b["
    black = "30"
    red = "31"
    green = "32"
    yellow = "33"
    blue = "34"
    magenta = "35"
    cyan = "36"
    white = "37"
    reset = "0"
    bold = "1"
    italic = "3"
    underline = "4"
    default = "39"

    @classmethod
    def colorize(cls, text: str, color: str, bold: bool = False, underline: bool = False, italic: bool = False) -> str:
        colour = [getattr(cls, color, "39")]
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
    def paint_black(cls, text: str, bold: bool = False, underline: bool = False, italic: bool = False) -> str:
        return cls.colorize(text, "black", bold, underline, italic)

    @classmethod
    def paint_red(cls, text: str, bold: bool = False, underline: bool = False, italic: bool = False) -> str:
        return cls.colorize(text, "red", bold, underline, italic)

    @classmethod
    def paint_green(cls, text: str, bold: bool = False, underline: bool = False, italic: bool = False) -> str:
        return cls.colorize(text, "green", bold, underline, italic)

    @classmethod
    def paint_yellow(cls, text: str, bold: bool = False, underline: bool = False, italic: bool = False) -> str:
        return cls.colorize(text, "yellow", bold, underline, italic)

    @classmethod
    def paint_blue(cls, text: Any, bold: bool = False, underline: bool = False, italic: bool = False) -> str:
        return cls.colorize(text, "blue", bold, underline, italic)

    @classmethod
    def paint_magenta(cls, text: str, bold: bool = False, underline: bool = False, italic: bool = False) -> str:
        return cls.colorize(text, "magenta", bold, underline, italic)

    @classmethod
    def paint_cyan(cls, text: str, bold: bool = False, underline: bool = False, italic: bool = False) -> str:
        return cls.colorize(text, "cyan", bold, underline, italic)

    @classmethod
    def paint_white(cls, text: str, bold: bool = False, underline: bool = False, italic: bool = False) -> str:
        return cls.colorize(text, "white", bold, underline, italic)

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
        color_diffs = []
        for name, color in COLOURS.items():
            cr, cg, cb = color
            color_diff = sqrt((red - cr) ** 2 + (green - cg) ** 2 + (blue - cb) ** 2)
            color_diffs.append((color_diff, name))
        return min(color_diffs)[1]
