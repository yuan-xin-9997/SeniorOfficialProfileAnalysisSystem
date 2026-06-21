import requests
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.models import SourceConfig, SourceDocument
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, require_admin
from app.modules.sources.crawler import crawl_source_config, read_excerpt
from app.modules.sources.profile_parser import parse_source_document_profile
from app.modules.sources.schemas import (
    SourceConfigCreate,
    SourceConfigRead,
    SourceConfigUpdate,
    SourceDocumentRead,
    SourceParseResult,
)

router = APIRouter()


@router.get("/configs", response_model=list[SourceConfigRead])
def list_source_configs(
    enabled: bool | None = Query(default=None),
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[SourceConfig]:
    query = db.query(SourceConfig)
    if enabled is not None:
        query = query.filter(SourceConfig.is_enabled == enabled)
    return query.order_by(SourceConfig.created_at.desc()).all()


@router.post("/configs", response_model=SourceConfigRead, status_code=status.HTTP_201_CREATED)
def create_source_config(
    payload: SourceConfigCreate,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SourceConfig:
    config = SourceConfig(**payload.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.patch("/configs/{config_id}", response_model=SourceConfigRead)
def update_source_config(
    config_id: str,
    payload: SourceConfigUpdate,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SourceConfig:
    config = db.get(SourceConfig, config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source config not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config


@router.post("/configs/{config_id}/crawl", response_model=SourceDocumentRead)
def crawl_config_now(
    config_id: str,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    config = db.get(SourceConfig, config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source config not found")
    if not config.is_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source config is disabled")
    try:
        document = crawl_source_config(db, config)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Crawl failed: {exc}",
        ) from exc
    return serialize_document(document)


@router.get("/documents", response_model=list[SourceDocumentRead])
def list_source_documents(
    source_config_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = db.query(SourceDocument)
    if source_config_id:
        query = query.filter(SourceDocument.source_config_id == source_config_id)
    documents = query.order_by(SourceDocument.fetched_at.desc()).limit(limit).all()
    return [serialize_document(document) for document in documents]


@router.post("/documents/{document_id}/parse-profile", response_model=SourceParseResult)
def parse_document_profile(
    document_id: str,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    document = db.get(SourceDocument, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source document not found")
    result = parse_source_document_profile(db, document)
    return {
        "official_id": result.official_id,
        "official_name": result.official_name,
        "created_events": result.created_events,
        "skipped_duplicates": result.skipped_duplicates,
        "parsed_candidates": result.parsed_candidates,
        "message": result.message,
    }


def serialize_document(document: SourceDocument) -> dict:
    return {
        "id": document.id,
        "source_config_id": document.source_config_id,
        "url": document.url,
        "title": document.title,
        "publisher": document.publisher,
        "fetched_at": document.fetched_at,
        "http_status": document.http_status,
        "content_hash": document.content_hash,
        "raw_html_path": document.raw_html_path,
        "plain_text_path": document.plain_text_path,
        "trust_level": document.trust_level,
        "parse_status": document.parse_status,
        "created_at": document.created_at,
        "plain_text_excerpt": read_excerpt(document.plain_text_path),
    }
