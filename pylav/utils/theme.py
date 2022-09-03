from __future__ import annotations

from typing import Any


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
