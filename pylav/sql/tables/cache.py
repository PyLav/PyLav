from __future__ import annotations

from piccolo.columns import Bytea, Text
from piccolo.table import Table

from pylav.sql.tables.init import DB


class AioHttpCacheRow(Table, db=DB, tablename="aiohttp_client_cache"):
    key = Text(primary_key=True, index=True)
    value = Bytea()
