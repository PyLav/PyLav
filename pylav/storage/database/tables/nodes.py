from __future__ import annotations

from piccolo.columns import JSONB, UUID, Array, BigInt, Boolean, Integer, Text
from piccolo.table import Table

from pylav.storage.database.tables.misc import DATABASE_ENGINE


class NodeRow(Table, db=DATABASE_ENGINE, tablename="node"):
    id = BigInt(primary_key=True, index=True)
    name = Text(null=False)
    ssl = Boolean(null=False, default=False)
    resume_key = Text(null=True, default=None)
    resume_timeout = Integer(null=False, default=600)
    reconnect_attempts = Integer(null=False, default=-1)
    search_only = Boolean(null=False, default=False)
    managed = Boolean(null=False, default=False)
    disabled_sources = Array(null=False, default=[], base_column=Text())
    extras = JSONB(null=True, default={})
    yaml = JSONB(null=True, default={})


class Sessions(Table, db=DATABASE_ENGINE, tablename="sessions"):
    primary_key = UUID(primary_key=True)
    bot = BigInt(index=True)
    node = BigInt(index=True)
    id = Text(null=True)
