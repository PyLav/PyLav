from __future__ import annotations

from piccolo.columns import BigInt, Text
from piccolo.table import Table

from pylav.constants.versions import VERSION_0_0_0
from pylav.storage.database.tables.misc import DATABASE_ENGINE


class BotVersionRow(Table, db=DATABASE_ENGINE, tablename="version"):
    bot = BigInt(primary_key=True, index=True)
    version = Text(null=False, default=str(VERSION_0_0_0))
