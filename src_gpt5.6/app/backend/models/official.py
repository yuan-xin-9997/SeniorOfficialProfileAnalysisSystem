"""高级官员履历、任职经历与人物关系模型。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from ..core.timeutil import utcnow


class Official(Base):
    __tablename__ = "officials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    gender: Mapped[str] = mapped_column(String(16), default="")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ethnicity: Mapped[str] = mapped_column(String(64), default="")
    native_place: Mapped[str] = mapped_column(String(128), default="")
    education: Mapped[str] = mapped_column(String(255), default="")
    current_position: Mapped[str] = mapped_column(String(255), default="", index=True)
    organization: Mapped[str] = mapped_column(String(255), default="", index=True)
    administrative_rank: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="在任", index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    photo_url: Mapped[str] = mapped_column(String(1024), default="")
    source_url: Mapped[str] = mapped_column(String(1024), default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    careers: Mapped[list["Career"]] = relationship(
        back_populates="official", cascade="all, delete-orphan", order_by="Career.sort_order"
    )


class Career(Base):
    __tablename__ = "careers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    official_id: Mapped[int] = mapped_column(
        ForeignKey("officials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[str] = mapped_column(String(32), default="")
    end_date: Mapped[str] = mapped_column(String(32), default="至今")
    organization: Mapped[str] = mapped_column(String(255), default="")
    position: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(128), default="")
    administrative_rank: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    official: Mapped[Official] = relationship(back_populates="careers")


class OfficialRelation(Base):
    __tablename__ = "official_relations"
    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "relation_type", name="uq_official_relation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("officials.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("officials.id", ondelete="CASCADE"), index=True)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    source: Mapped[Official] = relationship(foreign_keys=[source_id])
    target: Mapped[Official] = relationship(foreign_keys=[target_id])
