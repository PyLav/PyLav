from __future__ import annotations

import datetime

from sqlalchemy import DATETIME, Column, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class QueryTrackDBEntry(Base):
    __tablename__ = "query_tracks_association"

    id = Column(ForeignKey("query.id"), primary_key=True)
    base64 = Column(ForeignKey("track.base64"), primary_key=True)

    query = relationship("QueryDBEntry", back_populates="tracks", lazy="joined")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TrackDBEntry(Base):
    __tablename__ = "track"
    base64 = Column(Text, primary_key=True, index=True)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class QueryDBEntry(Base):
    __tablename__ = "query"
    id = Column(Text, primary_key=True, index=True)
    name = Column(Text, nullable=True)
    last_updated = Column(DATETIME(), nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.utcnow)
    tracks = relationship("QueryTrackDBEntry", back_populates="query", lazy="joined")

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["tracks"] = [t.base64 for t in self.tracks]
        return data
