from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CommitteeTermRead(BaseModel):
    id: str
    term_no: int
    name: str
    start_year: int | None = None
    end_year: int | None = None
    is_current: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommitteeImportRequest(BaseModel):
    term_no: int = 20
    term_name: str = "中国共产党第二十届中央委员会"
    start_year: int = 2022
    end_year: int | None = 2027
    csv_text: str


class CommitteeImportResult(BaseModel):
    term_id: str
    created_officials: int
    updated_officials: int
    memberships_upserted: int
    skipped_rows: int

