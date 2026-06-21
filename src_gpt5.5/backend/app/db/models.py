from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def uuid_str() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="USER")
    display_name: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CommitteeTerm(Base, TimestampMixin):
    __tablename__ = "committee_terms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    term_no: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    start_year: Mapped[int | None] = mapped_column(Integer)
    end_year: Mapped[int | None] = mapped_column(Integer)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(128), index=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(64))
    province: Mapped[str | None] = mapped_column(String(64), index=True)
    city: Mapped[str | None] = mapped_column(String(64), index=True)
    county: Mapped[str | None] = mapped_column(String(64), index=True)
    level: Mapped[str | None] = mapped_column(String(32))
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("locations.id"))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 6))
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 6))
    aliases: Mapped[dict | list | None] = mapped_column(JSON)


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255), index=True)
    full_name: Mapped[str | None] = mapped_column(String(512))
    org_type: Mapped[str | None] = mapped_column(String(64), index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"))
    location_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("locations.id"))
    valid_from: Mapped[datetime | None] = mapped_column(Date)
    valid_to: Mapped[datetime | None] = mapped_column(Date)
    aliases: Mapped[dict | list | None] = mapped_column(JSON)


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255), index=True)
    normalized_name: Mapped[str | None] = mapped_column(String(255), index=True)
    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"))
    rank_level: Mapped[str | None] = mapped_column(String(64), index=True)
    position_type: Mapped[str | None] = mapped_column(String(64), index=True)
    aliases: Mapped[dict | list | None] = mapped_column(JSON)


class Official(Base, TimestampMixin):
    __tablename__ = "officials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(64), index=True)
    name_pinyin: Mapped[str | None] = mapped_column(String(128), index=True)
    aliases: Mapped[dict | list | None] = mapped_column(JSON)
    gender: Mapped[str | None] = mapped_column(String(16))
    ethnicity: Mapped[str | None] = mapped_column(String(32))
    birth_date: Mapped[datetime | None] = mapped_column(Date)
    birth_date_precision: Mapped[str] = mapped_column(String(16), default="unknown")
    native_place_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("locations.id"))
    birth_place_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("locations.id"))
    current_status: Mapped[str | None] = mapped_column(String(32))
    profile_photo_url: Mapped[str | None] = mapped_column(Text)
    profile_summary: Mapped[str | None] = mapped_column(Text)
    data_quality_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    review_status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    career_events: Mapped[list["CareerEvent"]] = relationship(back_populates="official")


class OfficialTermMembership(Base):
    __tablename__ = "official_term_memberships"
    __table_args__ = (UniqueConstraint("official_id", "term_id", name="uq_official_term"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("officials.id"), index=True)
    term_id: Mapped[str] = mapped_column(String(36), ForeignKey("committee_terms.id"), index=True)
    membership_type: Mapped[str] = mapped_column(String(32), index=True)
    rank_order: Mapped[int | None] = mapped_column(Integer)
    source_document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("source_documents.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class CareerEvent(Base, TimestampMixin):
    __tablename__ = "career_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("officials.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    start_date: Mapped[datetime | None] = mapped_column(Date, index=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, index=True)
    start_precision: Mapped[str] = mapped_column(String(16), default="unknown")
    end_precision: Mapped[str] = mapped_column(String(16), default="unknown")
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    position_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("positions.id"))
    location_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("locations.id"), index=True
    )
    description: Mapped[str] = mapped_column(Text)
    original_text: Mapped[str | None] = mapped_column(Text)
    is_concurrent: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5)
    review_status: Mapped[str] = mapped_column(String(32), default="pending_review", index=True)
    data_version: Mapped[int] = mapped_column(Integer, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    official: Mapped[Official] = relationship(back_populates="career_events")


class SourceConfig(Base, TimestampMixin):
    __tablename__ = "source_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255), index=True)
    base_url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(64), index=True)
    trust_level: Mapped[str] = mapped_column(String(8), default="B")
    crawl_strategy: Mapped[str] = mapped_column(String(64), default="requests")
    frequency_cron: Mapped[str] = mapped_column(String(64), default="0 3 * * 1")
    request_interval_seconds: Mapped[int] = mapped_column(Integer, default=3)
    max_retry: Mapped[int] = mapped_column(Integer, default=3)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_config_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("source_configs.id")
    )
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    raw_html_path: Mapped[str | None] = mapped_column(Text)
    plain_text_path: Mapped[str | None] = mapped_column(Text)
    trust_level: Mapped[str] = mapped_column(String(8), default="B")
    parse_status: Mapped[str] = mapped_column(String(32), default="unparsed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    field_name: Mapped[str | None] = mapped_column(String(128))
    source_document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_documents.id"), index=True
    )
    quote_text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class RelationshipWeightProfile(Base, TimestampMixin):
    __tablename__ = "relationship_weight_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))

    items: Mapped[list["RelationshipWeightItem"]] = relationship(back_populates="profile")


class RelationshipWeightItem(Base):
    __tablename__ = "relationship_weight_items"
    __table_args__ = (
        UniqueConstraint("profile_id", "relationship_type", name="uq_weight_profile_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("relationship_weight_profiles.id"), index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(64), index=True)
    base_weight: Mapped[float] = mapped_column(Numeric(8, 3))
    time_decay_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_score: Mapped[float] = mapped_column(Numeric(8, 3), default=100)
    description: Mapped[str | None] = mapped_column(Text)

    profile: Mapped[RelationshipWeightProfile] = relationship(back_populates="items")


class Relationship(Base, TimestampMixin):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    subject_official_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("officials.id"), index=True
    )
    object_official_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("officials.id"), index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(64), index=True)
    start_date: Mapped[datetime | None] = mapped_column(Date)
    end_date: Mapped[datetime | None] = mapped_column(Date)
    strength_score: Mapped[float] = mapped_column(Numeric(8, 3), default=0)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5)
    is_inferred: Mapped[bool] = mapped_column(Boolean, default=True)
    evidence_summary: Mapped[str | None] = mapped_column(Text)
    weight_profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("relationship_weight_profiles.id")
    )
    review_status: Mapped[str] = mapped_column(String(32), default="pending_review", index=True)


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255))
    task_type: Mapped[str] = mapped_column(String(64), index=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    parameters: Mapped[dict | list | None] = mapped_column(JSON)
    weight_profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("relationship_weight_profiles.id")
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    result_summary: Mapped[dict | list | None] = mapped_column(JSON)
    data_version: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), index=True)
    before_value: Mapped[dict | list | None] = mapped_column(JSON)
    after_value: Mapped[dict | list | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

