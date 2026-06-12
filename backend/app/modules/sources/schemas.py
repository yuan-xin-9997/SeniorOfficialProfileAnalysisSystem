from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceConfigCreate(BaseModel):
    name: str
    base_url: str
    source_type: str = "official"
    trust_level: str = "B"
    crawl_strategy: str = "requests"
    frequency_cron: str = "0 3 * * 1"
    request_interval_seconds: int = 3
    max_retry: int = 3
    is_enabled: bool = True


class SourceConfigUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    source_type: str | None = None
    trust_level: str | None = None
    crawl_strategy: str | None = None
    frequency_cron: str | None = None
    request_interval_seconds: int | None = None
    max_retry: int | None = None
    is_enabled: bool | None = None


class SourceConfigRead(BaseModel):
    id: str
    name: str
    base_url: str
    source_type: str
    trust_level: str
    crawl_strategy: str
    frequency_cron: str
    request_interval_seconds: int
    max_retry: int
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourceDocumentRead(BaseModel):
    id: str
    source_config_id: str | None = None
    url: str
    title: str | None = None
    publisher: str | None = None
    fetched_at: datetime
    http_status: int | None = None
    content_hash: str | None = None
    raw_html_path: str | None = None
    plain_text_path: str | None = None
    trust_level: str
    parse_status: str
    created_at: datetime
    plain_text_excerpt: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SourceParseResult(BaseModel):
    official_id: str | None = None
    official_name: str | None = None
    created_events: int
    skipped_duplicates: int
    parsed_candidates: int
    message: str
