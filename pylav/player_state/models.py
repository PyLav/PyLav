from __future__ import annotations

from sqlalchemy import BOOLEAN, JSON, TEXT, BigInteger, Column, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PlayerEntry(Base):
    __tablename__ = "player"
    guild_id = Column(BigInteger, primary_key=True)
    current = Column(TEXT, nullable=True)
    paused = Column(BOOLEAN, nullable=False, default=False)
    repeat_current = Column(BOOLEAN, nullable=False, default=False)
    repeat_queue = Column(BOOLEAN, nullable=False, default=False)
    shuffle = Column(BOOLEAN, nullable=False, default=False)
    auto_playing = Column(BOOLEAN, nullable=False, default=False)
    playing = Column(BOOLEAN, nullable=False, default=False)
    position = Column(BigInteger, nullable=False, default=0)
    effect_enabled = Column(BOOLEAN, nullable=False, default=False)
    volume = Column(Integer, nullable=False, default=100)

    queue = Column(JSON, nullable=False, default=[])
    metadata = Column(JSON, nullable=False, default={})
    effects = Column(JSON, nullable=False, default={})
    extras = Column(JSON, nullable=False, default={})

    def as_dict(self) -> dict:
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data
