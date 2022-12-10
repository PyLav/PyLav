from __future__ import annotations

import datetime

JSON_TYPE = dict[str, "JSON_TYPE"] | list["JSON_TYPE"] | str | int | float | bool | None
JSON_DICT_TYPE = dict[str, JSON_TYPE]

JSON_WITH_DATE_TYPE = (
    dict[str, "JSON_WITH_DATE_TYPE"] | list["JSON_WITH_DATE_TYPE"] | str | int | float | bool | None | datetime.datetime
)
JSON_DICT_WITH_DATE_TYPE = dict[str, JSON_WITH_DATE_TYPE]
