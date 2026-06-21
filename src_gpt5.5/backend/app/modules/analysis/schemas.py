from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AnalysisTaskCreate(BaseModel):
    name: str
    task_type: str
    parameters: dict[str, Any]
    weight_profile_id: str | None = None


class AnalysisTaskRead(BaseModel):
    id: str
    name: str
    task_type: str
    created_by: str | None = None
    parameters: dict[str, Any] | list[Any] | None = None
    weight_profile_id: str | None = None
    status: str
    result_summary: dict[str, Any] | list[Any] | None = None
    data_version: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

