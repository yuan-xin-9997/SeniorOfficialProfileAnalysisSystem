from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class RelationshipRead(BaseModel):
    id: str
    subject_official_id: str
    object_official_id: str
    subject_name: str | None = None
    object_name: str | None = None
    relationship_type: str
    start_date: date | None = None
    end_date: date | None = None
    strength_score: float
    confidence: float
    is_inferred: bool
    evidence_summary: str | None = None
    review_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WeightItemRead(BaseModel):
    id: str
    relationship_type: str
    base_weight: float
    time_decay_enabled: bool
    max_score: float
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WeightProfileRead(BaseModel):
    id: str
    name: str
    is_default: bool
    items: list[WeightItemRead] = []

    model_config = ConfigDict(from_attributes=True)


class WeightItemUpdate(BaseModel):
    relationship_type: str
    base_weight: float
    max_score: float = 100
    time_decay_enabled: bool = True
    description: str | None = None


class WeightProfileCreate(BaseModel):
    name: str
    is_default: bool = False
    items: list[WeightItemUpdate]


class RelationshipRebuildResult(BaseModel):
    generated_relationships: int
    relationship_types: int
