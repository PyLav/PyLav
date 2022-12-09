def shorten_string(string: str, max_length: int, right: bool = True) -> str:
    if not string:
        return string
    if len(string) > max_length:
        if right:
            return string[: max_length - 1] + "\N{HORIZONTAL ELLIPSIS}"
        else:
            return string[(max_length - 1) * -1 :] + "\N{HORIZONTAL ELLIPSIS}"
    return string
