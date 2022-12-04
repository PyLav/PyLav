from __future__ import annotations

from piccolo.columns import Bytea, Text
from piccolo.table import Table

from pylav.storage.database.tables.misc import DATABASE_ENGINE


class AioHttpCacheRow(Table, db=DATABASE_ENGINE, tablename="aiohttp_client_cache"):
    key = Text(primary_key=True, index=True)
    value = Bytea()
