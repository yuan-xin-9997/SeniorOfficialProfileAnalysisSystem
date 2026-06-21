from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import CareerEvent, Location, Official, Organization, Position
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, require_admin
from app.modules.officials.schemas import (
    CareerEventCreate,
    CareerEventRead,
    OfficialCreate,
    OfficialRead,
    OfficialUpdate,
)

router = APIRouter()


@router.get("", response_model=list[OfficialRead])
def list_officials(
    q: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Official]:
    query = db.query(Official).filter(Official.deleted_at.is_(None))
    if q:
        pattern = f"%{q}%"
        query = query.filter(or_(Official.name.like(pattern), Official.profile_summary.like(pattern)))
    if review_status:
        query = query.filter(Official.review_status == review_status)
    return query.order_by(Official.name.asc()).offset(offset).limit(limit).all()


@router.post("", response_model=OfficialRead, status_code=status.HTTP_201_CREATED)
def create_official(
    payload: OfficialCreate,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Official:
    official = Official(**payload.model_dump())
    db.add(official)
    db.commit()
    db.refresh(official)
    return official


@router.get("/{official_id}", response_model=OfficialRead)
def get_official(
    official_id: str,
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Official:
    official = db.get(Official, official_id)
    if not official or official.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Official not found")
    return official


@router.patch("/{official_id}", response_model=OfficialRead)
def update_official(
    official_id: str,
    payload: OfficialUpdate,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Official:
    official = db.get(Official, official_id)
    if not official or official.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Official not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(official, key, value)
    db.commit()
    db.refresh(official)
    return official


@router.get("/{official_id}/timeline", response_model=list[CareerEventRead])
def get_timeline(
    official_id: str,
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CareerEvent]:
    events = (
        db.query(CareerEvent)
        .filter(CareerEvent.official_id == official_id, CareerEvent.deleted_at.is_(None))
        .order_by(CareerEvent.start_date.asc().nulls_last(), CareerEvent.created_at.asc())
        .all()
    )
    return [serialize_event(db, event) for event in events]


@router.post("/{official_id}/timeline", response_model=CareerEventRead)
def create_timeline_event(
    official_id: str,
    payload: CareerEventCreate,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CareerEvent:
    official = db.get(Official, official_id)
    if not official or official.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Official not found")
    payload_data = payload.model_dump()
    organization_name = payload_data.pop("organization_name", None)
    position_name = payload_data.pop("position_name", None)
    location_name = payload_data.pop("location_name", None)
    organization = ensure_organization(db, organization_name)
    location = ensure_location(db, location_name)
    position = ensure_position(db, position_name, organization.id if organization else None)
    event = CareerEvent(
        official_id=official_id,
        organization_id=organization.id if organization else None,
        location_id=location.id if location else None,
        position_id=position.id if position else None,
        **payload_data,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return serialize_event(db, event)


def ensure_organization(db: Session, name: str | None) -> Organization | None:
    if not name or not name.strip():
        return None
    normalized = name.strip()
    organization = db.query(Organization).filter(Organization.name == normalized).first()
    if organization:
        return organization
    organization = Organization(name=normalized, full_name=normalized, org_type="unknown")
    db.add(organization)
    db.flush()
    return organization


def ensure_location(db: Session, name: str | None) -> Location | None:
    if not name or not name.strip():
        return None
    normalized = name.strip()
    location = db.query(Location).filter(Location.name == normalized).first()
    if location:
        return location
    location = Location(name=normalized, full_name=normalized, country="中国", level="unknown")
    db.add(location)
    db.flush()
    return location


def ensure_position(
    db: Session,
    name: str | None,
    organization_id: str | None = None,
) -> Position | None:
    if not name or not name.strip():
        return None
    normalized = name.strip()
    query = db.query(Position).filter(Position.name == normalized)
    if organization_id:
        query = query.filter(Position.organization_id == organization_id)
    position = query.first()
    if position:
        return position
    position = Position(
        name=normalized,
        normalized_name=normalized,
        organization_id=organization_id,
        position_type="unknown",
    )
    db.add(position)
    db.flush()
    return position


def serialize_event(db: Session, event: CareerEvent) -> dict:
    organization = db.get(Organization, event.organization_id) if event.organization_id else None
    position = db.get(Position, event.position_id) if event.position_id else None
    location = db.get(Location, event.location_id) if event.location_id else None
    return {
        "id": event.id,
        "official_id": event.official_id,
        "event_type": event.event_type,
        "start_date": event.start_date,
        "end_date": event.end_date,
        "start_precision": event.start_precision,
        "end_precision": event.end_precision,
        "organization_name": organization.name if organization else None,
        "position_name": position.name if position else None,
        "location_name": location.name if location else None,
        "description": event.description,
        "original_text": event.original_text,
        "confidence": float(event.confidence),
        "review_status": event.review_status,
    }
