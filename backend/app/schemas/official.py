from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EducationIn(BaseModel):
    institution: str
    major: str | None = None
    degree: str | None = None
    is_overseas: bool = False


class PoliticalCareerIn(BaseModel):
    location: str
    department: str | None = None
    position: str
    level: str | None = None
    secretary_id: UUID | None = None
    colleagues: list[UUID] | None = None
    superior_id: UUID | None = None


class CareerEntryIn(BaseModel):
    start_year: int
    end_year: int | None = None
    entry_type: str
    description: str
    education: EducationIn | None = None
    political_career: PoliticalCareerIn | None = None


class OfficialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    birth_date: date
    birth_place: str
    ancestral_home: str | None = None
    ethnicity: str | None = None
    political_affiliation: str | None = None
    gender: str
    photo_url: str | None = None
    current_position: str | None = None
    current_level: str | None = None
    committee_term: str
    committee_type: str
    status: str = "active"
    career_entries: list[CareerEntryIn] = Field(default_factory=list)


class OfficialUpdate(BaseModel):
    name: str | None = None
    birth_date: date | None = None
    birth_place: str | None = None
    ancestral_home: str | None = None
    ethnicity: str | None = None
    political_affiliation: str | None = None
    gender: str | None = None
    photo_url: str | None = None
    current_position: str | None = None
    current_level: str | None = None
    committee_term: str | None = None
    committee_type: str | None = None
    status: str | None = None


class EducationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution: str
    major: str | None
    degree: str | None
    is_overseas: bool


class PoliticalCareerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location: str
    department: str | None
    position: str
    level: str | None
    secretary_id: UUID | None
    colleagues: list[UUID] | None
    superior_id: UUID | None


class CareerEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    start_year: int
    end_year: int | None
    entry_type: str
    description: str
    education: EducationOut | None = None
    political_career: PoliticalCareerOut | None = None


class OfficialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    birth_date: date
    birth_place: str
    ancestral_home: str | None
    ethnicity: str | None
    political_affiliation: str | None
    gender: str
    photo_url: str | None
    current_position: str | None
    current_level: str | None
    committee_term: str
    committee_type: str
    status: str
    completeness_score: float
    created_at: datetime
    updated_at: datetime


class OfficialDetail(OfficialOut):
    career_entries: list[CareerEntryOut] = Field(default_factory=list)
