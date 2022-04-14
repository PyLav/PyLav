from __future__ import annotations

import datetime

from sqlalchemy import DATETIME, INTEGER, BigInteger, Column, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class PlaylistTrackDBEntry(Base):
    __tablename__ = "playlist_track_association"

    id = Column(ForeignKey("playlist.id"), primary_key=True)
    base64 = Column(ForeignKey("track.base64"), primary_key=True)
    playlist = relationship("PlaylistDBEntry", back_populates="tracks", lazy="joined")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class PlaylistDBEntry(Base):
    __tablename__ = "playlist"

    id = Column(BigInteger, primary_key=True)
    scope = Column(INTEGER, nullable=False, index=True)
    scope_id = Column(BigInteger, nullable=False, index=True)
    author = Column(BigInteger, nullable=False, index=True)
    name = Column(Text, nullable=False, index=True)
    url = Column(Text, nullable=True)
    last_updated = Column(DATETIME, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.utcnow)
    tracks = relationship("PlaylistTrackDBEntry", back_populates="playlist", lazy="joined")

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["tracks"] = [t.base64 for t in self.tracks]
        return data


class TrackDBEntry(Base):
    __tablename__ = "track"
    base64 = Column(Text, primary_key=True, index=True)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
