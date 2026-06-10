import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Official(Base):
    __tablename__ = "officials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_place: Mapped[str] = mapped_column(String(128), nullable=False)
    ancestral_home: Mapped[str | None] = mapped_column(String(128))
    ethnicity: Mapped[str | None] = mapped_column(String(32))
    political_affiliation: Mapped[str | None] = mapped_column(String(64))
    gender: Mapped[str] = mapped_column(String(8), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text)
    current_position: Mapped[str | None] = mapped_column(String(256))
    current_level: Mapped[str | None] = mapped_column(String(64))
    committee_term: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    committee_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    career_entries: Mapped[list["CareerEntry"]] = relationship(back_populates="official", cascade="all, delete-orphan")


class CareerEntry(Base):
    __tablename__ = "career_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    official_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("officials.id", ondelete="CASCADE"), index=True)
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[int | None] = mapped_column(Integer)
    entry_type: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    official: Mapped["Official"] = relationship(back_populates="career_entries")
    education: Mapped["Education | None"] = relationship(back_populates="career_entry", uselist=False, cascade="all, delete-orphan")
    political_career: Mapped["PoliticalCareer | None"] = relationship(
        back_populates="career_entry", uselist=False, cascade="all, delete-orphan"
    )


class Education(Base):
    __tablename__ = "education"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    career_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("career_entries.id", ondelete="CASCADE"), unique=True
    )
    institution: Mapped[str] = mapped_column(String(256), nullable=False)
    major: Mapped[str | None] = mapped_column(String(128))
    degree: Mapped[str | None] = mapped_column(String(32))
    is_overseas: Mapped[bool] = mapped_column(default=False)

    career_entry: Mapped["CareerEntry"] = relationship(back_populates="education")


class PoliticalCareer(Base):
    __tablename__ = "political_career"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    career_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("career_entries.id", ondelete="CASCADE"), unique=True
    )
    location: Mapped[str] = mapped_column(String(128), nullable=False)
    department: Mapped[str | None] = mapped_column(String(256))
    position: Mapped[str] = mapped_column(String(256), nullable=False)
    level: Mapped[str | None] = mapped_column(String(64))
    secretary_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    colleagues: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    superior_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    career_entry: Mapped["CareerEntry"] = relationship(back_populates="political_career")


class Relationship(Base):
    __tablename__ = "relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_official_id",
            "target_official_id",
            "relationship_type",
            "location",
            "department",
            name="uq_relationship",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_official_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("officials.id", ondelete="CASCADE"), index=True)
    target_official_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("officials.id", ondelete="CASCADE"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    context: Mapped[str | None] = mapped_column(Text)
    start_year: Mapped[int | None] = mapped_column(Integer)
    end_year: Mapped[int | None] = mapped_column(Integer)
    location: Mapped[str | None] = mapped_column(String(128))
    department: Mapped[str | None] = mapped_column(String(256))
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
