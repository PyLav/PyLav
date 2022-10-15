from __future__ import annotations

from piccolo.columns import BigInt, Text
from piccolo.table import Table

from pylav.sql.tables.init import DB


class BotVersionRow(Table, db=DB, tablename="version"):
    bot = BigInt(primary_key=True, index=True)
    version = Text(null=False, default="0.0.0")
