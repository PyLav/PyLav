from __future__ import annotations

import datetime

from sqlalchemy import DATETIME, FLOAT, INTEGER, BigInteger, Column, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class EqualizerDBEntry(Base):
    __tablename__ = "equalizer"
    id = Column(BigInteger, primary_key=True)
    scope = Column(INTEGER, nullable=False, index=True)
    scope_id = Column(BigInteger, nullable=False, index=True)
    name = Column(Text, nullable=True, index=True)
    description = Column(Text, nullable=True)
    author = Column(BigInteger, nullable=False, index=True)
    band_25 = Column(FLOAT, nullable=False, default=0.0)
    band_40 = Column(FLOAT, nullable=False, default=0.0)
    band_63 = Column(FLOAT, nullable=False, default=0.0)
    band_100 = Column(FLOAT, nullable=False, default=0.0)
    band_160 = Column(FLOAT, nullable=False, default=0.0)
    band_250 = Column(FLOAT, nullable=False, default=0.0)
    band_400 = Column(FLOAT, nullable=False, default=0.0)
    band_630 = Column(FLOAT, nullable=False, default=0.0)
    band_1000 = Column(FLOAT, nullable=False, default=0.0)
    band_1600 = Column(FLOAT, nullable=False, default=0.0)
    band_2500 = Column(FLOAT, nullable=False, default=0.0)
    band_4000 = Column(FLOAT, nullable=False, default=0.0)
    band_6300 = Column(FLOAT, nullable=False, default=0.0)
    band_10000 = Column(FLOAT, nullable=False, default=0.0)
    band_16000 = Column(FLOAT, nullable=False, default=0.0)
    last_updated = Column(DATETIME(), nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data

    @staticmethod
    def before_set_band(target, value, oldvalue, initiator):
        if not (-0.25 <= value <= 1.0):
            raise ValueError(f"{target.name} must be between -0.25 and 1.0")

    def as_eq_compatible(self) -> dict[str, list[dict[str, float | int]] | str | int | None]:
        _dict = {
            0: self.band_25,
            1: self.band_40,
            2: self.band_63,
            3: self.band_100,
            4: self.band_160,
            5: self.band_250,
            6: self.band_400,
            7: self.band_630,
            8: self.band_1000,
            9: self.band_1600,
            10: self.band_2500,
            11: self.band_4000,
            12: self.band_6300,
            13: self.band_10000,
            14: self.band_16000,
        }

        data = dict(
            id=self.id,
            equalizer=[{"band": i, "gain": _dict[i]} for i in range(15)],
            name=self.name,
            description=self.description,
            author=self.author,
            scope=self.scope,
            scope_id=self.scope_id,
        )
        return data

    @classmethod
    def get_dict_from_eq_compat(cls, data_compat: dict) -> dict[str, float | str | int | None]:
        data = dict(
            id=data_compat["id"],
            name=data_compat["name"],
            description=data_compat["description"],
            author=data_compat["author"],
            scope=data_compat["scope"],
            scope_id=data_compat["scope_id"],
            band_25=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 0), 0.0),
            band_40=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 1), 0.0),
            band_63=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 2), 0.0),
            band_100=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 3), 0.0),
            band_160=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 4), 0.0),
            band_250=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 5), 0.0),
            band_400=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 6), 0.0),
            band_630=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 7), 0.0),
            band_1000=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 8), 0.0),
            band_1600=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 9), 0.0),
            band_2500=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 10), 0.0),
            band_4000=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 11), 0.0),
            band_6300=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 12), 0.0),
            band_10000=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 13), 0.0),
            band_16000=next((i["gain"] for i in data_compat["equalizer"] if i["band"] == 14), 0.0),
        )
        return data
