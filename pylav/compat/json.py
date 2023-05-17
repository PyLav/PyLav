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
        """Serialize ``obj`` to a JSON formatted ``str``."""
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
        """Serialize ``obj`` to a JSON formatted ``str``."""
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
        """Serialize ``obj`` to a JSON formatted ``str``."""
        ...

    __dumps_origin = json


# .loads() signatures
if _orjson:

    @overload
    def loads(obj: bytes | bytearray | memoryview | str) -> Any:
        """Deserialize ``obj`` (a ``str``, ``bytes`` or ``bytearray`` instance"""
        ...

    __loads_origin = _orjson

elif _ujson:

    @overload
    def loads(obj: AnyStr, *, ujson_precise_float: bool | None = None) -> Any:
        """Deserialize ``obj`` (a ``str``, ``bytes`` or ``bytearray`` instance"""
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
        """Deserialize ``obj`` (a ``str``, ``bytes`` or ``bytearray`` instance"""
        ...

    __loads_origin = json


# .dump() signatures
if _orjson:

    @overload
    def dump(
        obj: Any,
        fp: IO[str],
    ) -> None:
        """Serialize ``obj`` as a JSON formatted stream to ``fp`` (a ``.write()``-supporting file-like object)."""
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
        """Serialize ``obj`` as a JSON formatted stream to ``fp`` (a ``.write()``-supporting file-like object)."""
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
        """Serialize ``obj`` as a JSON formatted stream to ``fp`` (a ``.write()``-supporting file-like object)."""
        ...

    __dump_origin = json


# .load() signatures

if _orjson:

    @overload
    def load(fp: IO[AnyStr]) -> Any:
        """Deserialize ``fp`` (a ``.read()``-supporting file-like object containing a JSON document) to a Python object."""
        ...

    __load_origin = _orjson

elif _ujson:

    @overload
    def load(
        fp: IO[AnyStr],
        *,
        precise_float: bool = ...,
    ) -> Any:
        """Deserialize ``fp`` (a ``.read()``-supporting file-like object containing a JSON document) to a Python object."""
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
        """Deserialize ``fp`` (a ``.read()``-supporting file-like object containing a JSON document) to a Python object."""
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
    """
    Serialize ``obj`` to a JSON formatted ``str``.

    Parameters
    ----------
    obj : Any
        The object to serialize.
    skipkeys : bool, optional
        If ``True`` (default: ``False``), keys that are not basic types (``str``, ``int``, ``float``, ``bool``, ``None``) will be skipped instead of raising a ``TypeError``.
    ensure_ascii: bool, optional
        If ``True`` (default: ``True``), the output is guaranteed to have all incoming non-ASCII characters escaped. If ``False``, these characters will be output as-is.
    check_circular: bool, optional
        If check_circular is ``False`` (default: ``True``), then the circular reference check for container types will be skipped and a circular reference will result in an ``RecursionError`` (or worse).
    allow_nan: bool, optional
        If ``False`` (default: ``True``), then it will be a ValueError to serialize out of range float values (`nan`, `inf`, `-inf`) in strict compliance of the JSON specification. If ``True``, their JavaScript equivalents (`NaN`, `Infinity`, `-Infinity`) will be used.
    cls : type, optional
        If specified, must be a subclass of ``json.JSONEncoder``. An instance is used to encode the object.
    indent : int or str, optional
        If specified, then JSON array elements and object members will be pretty-printed with a newline followed by that many spaces. An indent level of 0, negative, or ``None`` will only insert newlines. ``None`` is the most compact representation. Using a negative indent indents that many spaces after the ``newline`` character. If it is a string (such as ``'\t'``), that string is used to indent each level. Default: ``None``.
    separators : tuple, optional
        If specified, then it should be an (item_separator, key_separator) tuple. The default is ``(', ', ': ')`` if *indent* is ``None`` and ``(',', ': ')`` otherwise. To get the most compact JSON representation, you should specify ``(',', ':')`` to eliminate whitespace.
    default: Callable, optional
        If specified, then it should be a function that gets called for objects that can't otherwise be serialized. It should return a JSON encodable version of the object or raise a ``TypeError``. If not specified, ``TypeError`` is raised.
    sort_keys: bool, optional
        If ``True`` (default: ``False``), then the output of dictionaries will be sorted by key.
    orjson_default: Callable, optional
        If specified, then it should be a function that gets called for objects that can't otherwise be serialized. It should return a JSON encodable version of the object or raise a ``TypeError``. If not specified, ``TypeError`` is raised.
    orjson_option: int, optional
        If specified, then it should be an integer that is passed to ``orjson.dumps`` as the ``option`` parameter. If not specified, ``None`` is used.
    ujson_encode_html_chars: bool, optional
        If ``True`` (default: ``False``), then the output will have the characters ``<``, ``>``, ``&`` encoded as ``\u003c``, ``\u003e``, ``\u0026``.
    ujson_escape_forward_slashes:
        If ``True`` (default: ``True``), then the output will have the forward slash character ``/`` encoded as ``\\/``.
    kwargs: Any, optional
        Additional keyword arguments are passed to ``json.dumps``.

    Returns
    -------
    str
        The JSON string representation of ``obj``.

    """
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
    """Deserialize ``obj`` (a ``str``, ``bytes`` or ``bytearray`` instance containing a JSON document) to a Python object.

    Parameters
    ----------
    obj: AnyStr | bytes | bytearray | memoryview | str
        The JSON string to deserialize.
    cls: type, optional
        If specified, must be a subclass of ``json.JSONDecoder``. An instance is used to decode the object.
    object_hook: Callable, optional
        If specified, then it should be a function that will be called with the result of any object literal decoded (a ``dict``). The return value of ``object_hook`` will be used instead of the ``dict``. This feature can be used to implement custom decoders (e.g. JSON-RPC class hinting).
    parse_float: Callable, optional
        If specified, then it should be a function to be called with the string of every JSON float to be decoded. By default this is equivalent to ``float(num_str)``. This can be used to use another datatype or parser for JSON floats (e.g. ``decimal.Decimal``).
    parse_int: Callable, optional
        If specified, then it should be a function to be called with the string of every JSON int to be decoded. By default this is equivalent to ``int(num_str)``. This can be used to use another datatype or parser for JSON integers (e.g. ``float``).
    parse_constant: Callable, optional
        If specified, then it should be a function to be called with one of the following strings: ``'-Infinity'``, ``'Infinity'``, ``'NaN'``. This can be used to raise an exception if invalid JSON numbers are encountered.
    object_pairs_hook: Callable, optional
        If specified, then it should be a function that will be called with the result of any object literal decoded with an ordered list of pairs. The return value of ``object_pairs_hook`` will be used instead of the ``dict``. This feature can be used to implement custom decoders. If ``object_hook`` is also defined, the ``object_pairs_hook`` takes priority.
    ujson_precise_float: bool, optional
        If ``True`` (default: ``False``), then
    kwargs: Any, optional
        Additional keyword arguments are passed to ``json.loads``.

    Returns
    -------
    Any
        The deserialized object.

    Raises
    ------
    json.JSONDecodeError
        If the input is not valid JSON.
    orjson.JSONDecodeError(json.JSONDecodeError, ValueError)
        If the input is not valid JSON and orjson is used.
    ValueError
        If the string is not correctly formed and ujson is used.

    """
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
    """Serialize ``obj`` as a JSON formatted stream to ``fp`` (a ``.write()``-supporting file-like object)."""

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
    """Deserialize ``fp`` (a ``.read()``-supporting file-like object containing a JSON document) to a Python object."""
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
    """Return a dict of json modules being used."""
    return {
        "dumps": __dumps_origin,
        "loads": __loads_origin,
        "dump": __dump_origin,
        "load": __load_origin,
    }
