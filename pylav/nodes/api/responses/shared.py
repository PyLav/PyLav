from __future__ import annotations

from dataclasses import _FIELD, _FIELDS, InitVar, dataclass, field  # noqa

_JSON_TYPE = dict[str, "_JSON_TYPE"] | list["_JSON_TYPE"] | str | int | float | bool | None
_JSON_DICT_TYPE = dict[str, _JSON_TYPE]


@dataclass()
class PluginInfo:
    kwargs: InitVar[_JSON_DICT_TYPE | None] = None

    def __post_init__(self, kwargs: _JSON_DICT_TYPE | None) -> None:
        if kwargs:
            for k, v in kwargs.items():
                object.__setattr__(self, k, v)

    def __getattr__(self, item):
        return None

    def __repr__(self):
        return f"PluginInfo({','.join([f'{key}={val!r}' for key, val in self.__dict__.items()])})"

    def _add_to_asdict(self, attr: str) -> None:
        f = field(repr=True)
        f.name = attr
        f._field_type = _FIELD
        getattr(self, _FIELDS)[attr] = f
