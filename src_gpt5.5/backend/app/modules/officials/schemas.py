from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class OfficialCreate(BaseModel):
    name: str
    gender: str | None = None
    ethnicity: str | None = None
    birth_date: date | None = None
    birth_date_precision: str = "unknown"
    current_status: str | None = None
    profile_summary: str | None = None
    review_status: str = "draft"


class OfficialUpdate(BaseModel):
    name: str | None = None
    gender: str | None = None
    ethnicity: str | None = None
    birth_date: date | None = None
    birth_date_precision: str | None = None
    current_status: str | None = None
    profile_summary: str | None = None
    review_status: str | None = None


class OfficialRead(BaseModel):
    id: str
    name: str
    gender: str | None = None
    ethnicity: str | None = None
    birth_date: date | None = None
    birth_date_precision: str
    current_status: str | None = None
    profile_summary: str | None = None
    data_quality_score: float | None = None
    review_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CareerEventCreate(BaseModel):
    event_type: str
    start_date: date | None = None
    end_date: date | None = None
    start_precision: str = "unknown"
    end_precision: str = "unknown"
    organization_name: str | None = None
    position_name: str | None = None
    location_name: str | None = None
    description: str
    original_text: str | None = None
    confidence: float = 0.5
    review_status: str = "verified"


class CareerEventRead(BaseModel):
    id: str
    official_id: str
    event_type: str
    start_date: date | None = None
    end_date: date | None = None
    start_precision: str
    end_precision: str
    organization_name: str | None = None
    position_name: str | None = None
    location_name: str | None = None
    description: str
    original_text: str | None = None
    confidence: float
    review_status: str

    model_config = ConfigDict(from_attributes=True)
