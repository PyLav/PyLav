from __future__ import annotations

from piccolo.columns import BigInt, Float, Text
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table

from pylav.storage.database.tables.misc import DATABASE_ENGINE


class EqualizerRow(Table, db=DATABASE_ENGINE, tablename="equalizer"):
    id = BigInt(primary_key=True, index=True)
    scope = BigInt(null=True, default=None, index=True)
    name = Text(null=True, default=None, index_method=IndexMethod.gin)
    description = Text(null=True, default=None)
    # FIXME: Drop existing table and recreate it with this column defaults
    # TODO: Handle new defaults
    author = BigInt(null=True, default=None, index=True)
    band_25 = Float(null=True, default=None)
    band_40 = Float(null=True, default=None)
    band_63 = Float(null=True, default=None)
    band_100 = Float(null=True, default=None)
    band_160 = Float(null=True, default=None)
    band_250 = Float(null=True, default=None)
    band_400 = Float(null=True, default=None)
    band_630 = Float(null=True, default=None)
    band_1000 = Float(null=True, default=None)
    band_1600 = Float(null=True, default=None)
    band_2500 = Float(null=True, default=None)
    band_4000 = Float(null=True, default=None)
    band_6300 = Float(null=True, default=None)
    band_10000 = Float(null=True, default=None)
    band_16000 = Float(null=True, default=None)
