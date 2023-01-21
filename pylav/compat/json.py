import contextlib
import json
from collections.abc import Callable
from json import JSONDecodeError as JSONDecodeError
from json import JSONDecoder as JSONDecoder
from json import JSONEncoder as JSONEncoder
from types import ModuleType
from typing import IO, Any, AnyStr, overload

try:
    import orjson as _orjson

except ImportError:
    _orjson = None

try:
    import ujson as _ujson
except ImportError:
    _ujson = None


__all__ = [
    "dump",
    "dumps",
    "load",
    "loads",
    "JSONDecoder",
    "JSONDecodeError",
    "JSONEncoder",
    "get_origin",
]

# .dumps() signatures
if _orjson:

    @overload
    def dumps(
        obj: Any,
        *,
        orjson_default: Callable[[Any], Any] | None = None,
        orjson_option: int | None = None,
    ) -> str:
        ...

    __dumps_origin = _orjson

elif _ujson:

    @overload
    def dumps(
        obj: Any,
        *,
        ensure_ascii: bool = True,
        ujson_encode_html_chars: bool = False,
        ujson_escape_forward_slashes: bool = True,
        sort_keys: bool = False,
        indent: int | None = 0,
    ) -> str:
        ...

    __dumps_origin = _ujson

else:

    @overload
    def dumps(
        obj: Any,
        *,
        skipkeys: bool = False,
        ensure_ascii: bool = True,
        check_circular: bool = True,
        allow_nan: bool = True,
        cls: type[JSONEncoder] | None = None,
        indent: None | int | str = None,
        separators: tuple[str, str] | None = None,
        default: Callable[[Any], Any] | None = None,
        sort_keys: bool = False,
        **kwds: Any,
    ) -> str:
        ...

    __dumps_origin = json


# .loads() signatures
if _orjson:

    @overload
    def loads(obj: bytes | bytearray | memoryview | str) -> Any:
        ...

    __loads_origin = _orjson

elif _ujson:

    @overload
    def loads(obj: AnyStr, *, ujson_precise_float: bool | None = None) -> Any:
        ...

    __loads_origin = _ujson

else:

    @overload
    def loads(
        obj: AnyStr,
        *,
        cls: type[JSONDecoder] | None = None,
        object_hook: Callable[[dict[Any, Any]], Any] | None = None,
        parse_float: Callable[[str], Any] | None = None,
        parse_int: Callable[[str], Any] | None = None,
        parse_constant: Callable[[str], Any] | None = None,
        object_pairs_hook: Callable[[list[tuple[Any, Any]]], Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        ...

    __loads_origin = json


# .dump() signatures
if _orjson:

    @overload
    def dump(
        obj: Any,
        fp: IO[str],
    ) -> None:
        ...

    __dump_origin = _orjson

elif _ujson:

    @overload
    def dump(
        obj: Any,
        fp: IO[str],
        *,
        ensure_ascii: bool = True,
        sort_keys: bool = False,
        indent: int = 0,
        ujson_encode_html_chars: bool = False,
        ujson_escape_forward_slashes: bool = True,
    ) -> None:
        ...

    __dump_origin = _ujson

else:

    @overload
    def dump(
        obj: Any,
        fp: IO[str],
        *,
        skipkeys: bool = False,
        ensure_ascii: bool = True,
        check_circular: bool = True,
        allow_nan: bool = True,
        cls: type[JSONEncoder] | None = None,
        indent: None | int | str = None,
        separators: tuple[str, str] | None = None,
        default: Callable[[Any], Any] | None = None,
        sort_keys: bool = False,
        **kwargs: Any,
    ) -> None:
        ...

    __dump_origin = json


# .load() signatures

if _orjson:

    @overload
    def load(fp: IO[AnyStr]) -> Any:
        ...

    __load_origin = _orjson

elif _ujson:

    @overload
    def load(
        fp: IO[AnyStr],
        *,
        precise_float: bool = ...,
    ) -> Any:
        ...

    __load_origin = _ujson

else:

    @overload
    def load(
        fp: IO[AnyStr],
        *,
        cls: type[JSONDecoder] | None = ...,
        object_hook: Callable[[Any], Any] | None = ...,
        parse_float: Callable[[str], float] | None = ...,
        parse_int: Callable[[str], int] | None = ...,
        parse_constant: Callable[[str], Any] | None = ...,
        object_pairs_hook: Callable[[list[tuple[str, Any]]], Any] | None = ...,
        **kwargs: Any,
    ) -> Any:
        ...

    __load_origin = json


def dumps(
    obj: Any,
    *,
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    cls=None,
    indent=None,
    separators=None,
    default=None,
    sort_keys=False,
    orjson_default=None,
    orjson_option=None,
    ujson_encode_html_chars=False,
    ujson_escape_forward_slashes=True,
    **kwargs,
) -> str:
    if _orjson:
        with contextlib.suppress(_orjson.JSONEncodeError):
            return _orjson.dumps(obj, default=orjson_default, option=orjson_option).decode()
    if _ujson:
        return _ujson.dumps(
            obj,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys,
            indent=indent or 0,
            encode_html_chars=ujson_encode_html_chars,
            escape_forward_slashes=ujson_escape_forward_slashes,
        )
    return json.dumps(
        obj,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        **kwargs,
    )


def loads(
    obj: AnyStr | bytes | bytearray | memoryview | str,
    *,
    cls=None,
    object_hook=None,
    parse_float=None,
    parse_int=None,
    parse_constant=None,
    object_pairs_hook=None,
    ujson_precise_float=None,
    **kwargs,
) -> Any:
    if _orjson:
        with contextlib.suppress(_orjson.JSONDecodeError):
            return _orjson.loads(obj)
    if _ujson:
        with contextlib.suppress(_ujson.JSONDecodeError):
            return _ujson.loads(obj, precise_float=ujson_precise_float)
    return json.loads(
        obj,
        cls=cls,
        object_hook=object_hook,
        parse_float=parse_float,
        parse_int=parse_int,
        parse_constant=parse_constant,
        object_pairs_hook=object_pairs_hook,
        **kwargs,
    )


def dump(
    obj: Any,
    fp: IO[AnyStr],
    *,
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    cls=None,
    indent=None,
    separators=None,
    default=None,
    sort_keys=False,
    ujson_encode_html_chars=False,
    ujson_escape_forward_slashes=True,
    **kwargs,
) -> None:
    if _orjson:
        with contextlib.suppress(_orjson.JSONEncodeError):
            fp.write(_orjson.dumps(obj).decode())
            return
    if _ujson:
        return _ujson.dump(
            obj,
            fp,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys,
            indent=indent or 0,
            encode_html_chars=ujson_encode_html_chars,
            escape_forward_slashes=ujson_escape_forward_slashes,
        )
    return json.dump(
        obj,
        fp,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        **kwargs,
    )


def load(
    fp: IO[AnyStr],
    *,
    cls=None,
    object_hook=None,
    parse_float=None,
    parse_int=None,
    parse_constant=None,
    object_pairs_hook=None,
    precise_float=None,
    **kwargs,
) -> Any:
    if _orjson:
        with contextlib.suppress(_orjson.JSONDecodeError):
            return _orjson.loads(fp.read())
    if _ujson:
        with contextlib.suppress(_ujson.JSONDecodeError):
            return _ujson.load(fp, precise_float=precise_float)
    return json.load(
        fp,
        cls=cls,
        object_hook=object_hook,
        parse_float=parse_float,
        parse_int=parse_int,
        parse_constant=parse_constant,
        object_pairs_hook=object_pairs_hook,
        **kwargs,
    )


def get_origin() -> dict[str, ModuleType]:
    return {
        "dumps": __dumps_origin,
        "loads": __loads_origin,
        "dump": __dump_origin,
        "load": __load_origin,
    }
