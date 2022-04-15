from __future__ import annotations

from sqlalchemy import TEXT, Boolean, Column, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class LibConfigEntry(Base):
    __tablename__ = "lib_config"
    id = Column(Integer, primary_key=True)
    db_connection_string = Column(TEXT, nullable=False, default="sqlite+aiosqlite:///")
    config_folder = Column(TEXT, nullable=False)
    java_path = Column(TEXT, nullable=False, default="java")
    enable_managed_node = Column(Boolean, nullable=False, default=True)
    auto_update_managed_nodes = Column(Boolean, nullable=False, default=True)

    def as_dict(self) -> dict:
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data
