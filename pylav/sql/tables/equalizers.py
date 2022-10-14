from __future__ import annotations

from piccolo.columns import BigInt, Float, Text
from piccolo.table import Table

from pylav.sql.tables.init import DB


class EqualizerRow(Table, db=DB, tablename="equalizer"):
    id = BigInt(primary_key=True, index=True)
    scope = BigInt(null=True, default=None)
    name = Text(null=True, default=None)
    description = Text(null=True, default=None)
    author = BigInt(null=True, default=None)
    band_25 = Float(null=False, default=0.0)
    band_40 = Float(null=False, default=0.0)
    band_63 = Float(null=False, default=0.0)
    band_100 = Float(null=False, default=0.0)
    band_160 = Float(null=False, default=0.0)
    band_250 = Float(null=False, default=0.0)
    band_400 = Float(null=False, default=0.0)
    band_630 = Float(null=False, default=0.0)
    band_1000 = Float(null=False, default=0.0)
    band_1600 = Float(null=False, default=0.0)
    band_2500 = Float(null=False, default=0.0)
    band_4000 = Float(null=False, default=0.0)
    band_6300 = Float(null=False, default=0.0)
    band_10000 = Float(null=False, default=0.0)
    band_16000 = Float(null=False, default=0.0)
