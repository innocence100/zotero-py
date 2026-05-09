import json
import secrets
import string
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    library_id: Mapped[int] = mapped_column(Integer, ForeignKey("libraries.id"), unique=True)

    library: Mapped["Library"] = relationship("Library", back_populates="user")
    api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="user")


class Library(Base):
    __tablename__ = "libraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(20), default="user")
    version: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    user: Mapped[Optional["User"]] = relationship("User", back_populates="library")
    items: Mapped[list["Item"]] = relationship(
        "Item", back_populates="library", cascade="all, delete-orphan"
    )
    collections: Mapped[list["Collection"]] = relationship(
        "Collection", back_populates="library", cascade="all, delete-orphan"
    )
    searches: Mapped[list["Search"]] = relationship(
        "Search", back_populates="library", cascade="all, delete-orphan"
    )
    settings: Mapped[list["Setting"]] = relationship(
        "Setting", back_populates="library", cascade="all, delete-orphan"
    )
    delete_log: Mapped[list["SyncDeleteLog"]] = relationship(
        "SyncDeleteLog", back_populates="library", cascade="all, delete-orphan"
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    access_json: Mapped[str] = mapped_column(Text, default='{"user":{"library":true,"write":true,"notes":true,"files":false},"groups":{"all":{"library":true,"write":true}}}')

    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    @property
    def access(self):
        return json.loads(self.access_json)


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(Integer, ForeignKey("libraries.id"))
    key: Mapped[str] = mapped_column(String(8), nullable=False)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    date_added: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    date_modified: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    parent_key: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    library: Mapped["Library"] = relationship("Library", back_populates="items")

    __table_args__ = (Index("ix_items_library_key", "library_id", "key", unique=True),)

    @property
    def data(self):
        return json.loads(self.data_json)

    @data.setter
    def data(self, value):
        self.data_json = json.dumps(value, ensure_ascii=False)


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(Integer, ForeignKey("libraries.id"))
    key: Mapped[str] = mapped_column(String(8), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_key: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    deleted: Mapped[int] = mapped_column(Integer, default=0)

    library: Mapped["Library"] = relationship("Library", back_populates="collections")

    __table_args__ = (Index("ix_collections_library_key", "library_id", "key", unique=True),)

    @property
    def data(self):
        return json.loads(self.data_json)

    @data.setter
    def data(self, value):
        self.data_json = json.dumps(value, ensure_ascii=False)


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(Integer, ForeignKey("libraries.id"))
    key: Mapped[str] = mapped_column(String(8), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    deleted: Mapped[int] = mapped_column(Integer, default=0)

    library: Mapped["Library"] = relationship("Library", back_populates="searches")

    __table_args__ = (Index("ix_searches_library_key", "library_id", "key", unique=True),)

    @property
    def data(self):
        return json.loads(self.data_json)

    @data.setter
    def data(self, value):
        self.data_json = json.dumps(value, ensure_ascii=False)


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(Integer, ForeignKey("libraries.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)

    library: Mapped["Library"] = relationship("Library", back_populates="settings")

    __table_args__ = (Index("ix_settings_library_name", "library_id", "name", unique=True),)

    @property
    def value(self):
        return json.loads(self.value_json)

    @value.setter
    def value(self, val):
        self.value_json = json.dumps(val, ensure_ascii=False)


class SyncDeleteLog(Base):
    __tablename__ = "sync_delete_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(Integer, ForeignKey("libraries.id"))
    object_type: Mapped[str] = mapped_column(String(20), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    library: Mapped["Library"] = relationship("Library", back_populates="delete_log")

    __table_args__ = (
        Index("ix_delete_log_library_version", "library_id", "version"),
    )


def generate_key(length=8):
    chars = "23456789ABCDEFGHIJKLMNPQRSTUVWXYZ"
    return "".join(secrets.choice(chars) for _ in range(length))
