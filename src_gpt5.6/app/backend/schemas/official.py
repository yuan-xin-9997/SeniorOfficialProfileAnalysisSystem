"""高级官员履历 API 数据结构。"""
from __future__ import annotations

from datetime import date

from pydantic import Field

from .common import BeijingDatetime, ORMBase


class CareerData(ORMBase):
    id: int | None = None
    start_date: str = ""
    end_date: str = "至今"
    organization: str = ""
    position: str
    location: str = ""
    administrative_rank: str = ""
    description: str = ""
    sort_order: int = 0


class OfficialBase(ORMBase):
    name: str = Field(min_length=1, max_length=128)
    gender: str = ""
    birth_date: date | None = None
    ethnicity: str = ""
    native_place: str = ""
    education: str = ""
    current_position: str = ""
    organization: str = ""
    administrative_rank: str = ""
    status: str = "在任"
    party_role: str = ""
    summary: str = ""
    photo_url: str = ""
    source_url: str = ""
    tags: list[str] = []


class OfficialCreate(OfficialBase):
    careers: list[CareerData] = []


class OfficialUpdate(OfficialCreate):
    pass


class OfficialBrief(OfficialBase):
    id: int
    created_at: BeijingDatetime
    updated_at: BeijingDatetime


class OfficialDetail(OfficialBrief):
    careers: list[CareerData]


class RelationCreate(ORMBase):
    source_id: int
    target_id: int
    relation_type: str
    description: str = ""


class RelationOut(RelationCreate):
    id: int
    source_name: str
    target_name: str
    created_at: BeijingDatetime


class RelationAnalysisRequest(ORMBase):
    source_id: int
    target_id: int


class RelationAnalysisResult(ORMBase):
    source_id: int
    target_id: int
    source_name: str
    target_name: str
    relation_type: str
    summary: str
    evidence: list[str] = []
    confidence: str = "中"


class OfficialPage(ORMBase):
    items: list[OfficialBrief]
    total: int
    page: int
    page_size: int


class TimelineRequest(ORMBase):
    official_ids: list[int] = Field(min_length=1, max_length=20)


class TimelineOfficial(ORMBase):
    id: int
    name: str
    current_position: str = ""
    organization: str = ""
    careers: list[CareerData]


class TimelineResult(ORMBase):
    officials: list[TimelineOfficial]


class DashboardStats(ORMBase):
    official_count: int
    active_count: int
    organization_count: int
    career_count: int
    relation_count: int
    recent_officials: list[OfficialBrief]
