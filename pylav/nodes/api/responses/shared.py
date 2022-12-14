from __future__ import annotations

from dataclasses import _FIELD, _FIELDS, InitVar, dataclass, field  # noqa

_JSON_TYPE = dict[str, "_JSON_TYPE"] | list["_JSON_TYPE"] | str | int | float | bool | None
_JSON_DICT_TYPE = dict[str, _JSON_TYPE]


@dataclass(repr=True, kw_only=True, slots=True)
class PluginInfo:
    kwargs: InitVar[_JSON_DICT_TYPE | None] = None

    def __post_init__(self, kwargs: _JSON_DICT_TYPE | None) -> None:
        if kwargs:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def _add_to_asdict(self, attr: str) -> None:
        f = field(repr=True)
        f.name = attr
        f._field_type = _FIELD
        getattr(self, _FIELDS)[attr] = f
