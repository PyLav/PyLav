from __future__ import annotations

from sqlalchemy import JSON, TEXT, BigInteger, Boolean, Column, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ConfigBase:
    __table__: ...

    def as_dict(self) -> dict:
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data


class GlobalConfigEntry(ConfigBase, Base):
    __tablename__ = "global_config"
    guild_id = Column(BigInteger, primary_key=True)


class GuildConfigEntry(ConfigBase, Base):
    __tablename__ = "guild_config"
    guild_id = Column(BigInteger, primary_key=True)


class UserConfigEntry(ConfigBase, Base):
    __tablename__ = "user_config"
    user_id = Column(BigInteger, primary_key=True)


class NodeConfigEntry(ConfigBase, Base):
    __tablename__ = "node_config"
    node_id = Column(BigInteger, primary_key=True)
    name = Column(TEXT, nullable=False)
    ssl = Column(Boolean, nullable=False, default=False)
    reconnect_attempts = Column(Integer, nullable=False)
    search_only = Column(Boolean, nullable=False, default=False)
    extras = Column(JSON, nullable=True)
