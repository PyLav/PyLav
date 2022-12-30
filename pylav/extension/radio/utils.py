from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps

from pylav.constants.radio import API_TYPES
from pylav.type_hints.generics import ANY_GENERIC_TYPE, PARAM_SPEC_TYPE


class Error(Exception):
    """Base class for all exceptions raised by this module"""


class IllegalArgumentError(Error):
    """Raised for illegal argument"""


def bool_to_string(boolean: bool) -> str:
    """Convert a boolean type to string.

    Args:
        boolean (bool): A Boolean.

    Raises:
        TypeError

    Returns:
        str: String representation of a bool type.
    """
    string = str(boolean).lower()
    if string in {"true", "false"}:
        return string
    raise TypeError("Value must be True or False")


def snake_to_camel(string: str) -> str:
    first, *others = string.split("_")
    return "".join([first.lower(), *map(str.title, others)])


def radio_browser_adapter(**kwargs: PARAM_SPEC_TYPE.kwargs) -> PARAM_SPEC_TYPE.kwargs:
    params = {}

    for key, value in kwargs.items():
        new_key = snake_to_camel(key)
        if isinstance(kwargs[key], bool):
            value = bool_to_string(value)
        params[new_key] = value
    return params


def validate_input(
    type_value: dict[str, type[str | bool | int]] | dict[str, str | int | bool],
    input_data: PARAM_SPEC_TYPE.kwargs,
) -> None:
    for key, value in input_data.items():
        try:
            key_type = type_value[key]
        except KeyError as exc:
            raise IllegalArgumentError(f"There is no parameter named '{exc.args[0]}'") from exc
        else:
            if not isinstance(value, key_type):
                raise TypeError(
                    "Argument {!r} must be {}, not {}".format(
                        key,
                        key_type.__name__,
                        type(value).__name__,
                    )
                )


def type_check(
    func: Callable[PARAM_SPEC_TYPE, Awaitable[ANY_GENERIC_TYPE]]  # type: ignore
) -> Callable[PARAM_SPEC_TYPE, Awaitable[ANY_GENERIC_TYPE]]:  # type: ignore
    @wraps(func)
    def wrapper(self, *args: PARAM_SPEC_TYPE.args, **kwargs: PARAM_SPEC_TYPE.kwargs) -> Awaitable[ANY_GENERIC_TYPE]:
        validate_input(API_TYPES[func.__name__], kwargs)
        kwargs = radio_browser_adapter(**kwargs)
        return func(self, *args, **kwargs)

    return wrapper
