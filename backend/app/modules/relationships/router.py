from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Official,
    Relationship,
    RelationshipWeightItem,
    RelationshipWeightProfile,
)
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, require_admin
from app.modules.relationships.schemas import (
    RelationshipRebuildResult,
    RelationshipRead,
    WeightProfileCreate,
    WeightProfileRead,
)
from app.modules.relationships.generator import rebuild_generated_relationships

router = APIRouter()


@router.get("", response_model=list[RelationshipRead])
def list_relationships(
    official_id: str | None = Query(default=None),
    relationship_type: str | None = Query(default=None),
    min_score: float = Query(default=0, ge=0, le=100),
    limit: int = Query(default=100, le=500),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = db.query(Relationship)
    if official_id:
        query = query.filter(
            or_(
                Relationship.subject_official_id == official_id,
                Relationship.object_official_id == official_id,
            )
        )
    if relationship_type:
        query = query.filter(Relationship.relationship_type == relationship_type)
    query = query.filter(Relationship.strength_score >= min_score)
    relationships = query.order_by(Relationship.strength_score.desc()).limit(limit).all()
    if not relationships:
        return []
    official_ids = {
        item.subject_official_id for item in relationships
    } | {item.object_official_id for item in relationships}
    names = {
        official.id: official.name
        for official in db.query(Official).filter(Official.id.in_(official_ids)).all()
    }
    return [serialize_relationship(item, names) for item in relationships]


@router.post("/rebuild", response_model=RelationshipRebuildResult)
def rebuild_relationships(
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    return rebuild_generated_relationships(db)


@router.get("/weight-profiles", response_model=list[WeightProfileRead])
def list_weight_profiles(
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RelationshipWeightProfile]:
    return (
        db.query(RelationshipWeightProfile)
        .options(selectinload(RelationshipWeightProfile.items))
        .order_by(RelationshipWeightProfile.is_default.desc(), RelationshipWeightProfile.name.asc())
        .all()
    )


@router.post(
    "/weight-profiles",
    response_model=WeightProfileRead,
    status_code=status.HTTP_201_CREATED,
)
def create_weight_profile(
    payload: WeightProfileCreate,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RelationshipWeightProfile:
    existing = (
        db.query(RelationshipWeightProfile)
        .filter(RelationshipWeightProfile.name == payload.name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile name exists")
    if payload.is_default:
        db.query(RelationshipWeightProfile).update({"is_default": False})
    profile = RelationshipWeightProfile(name=payload.name, is_default=payload.is_default)
    db.add(profile)
    db.flush()
    for item in payload.items:
        db.add(RelationshipWeightItem(profile_id=profile.id, **item.model_dump()))
    db.commit()
    db.refresh(profile)
    return profile


def serialize_relationship(item: Relationship, names: dict[str, str]) -> dict:
    return {
        "id": item.id,
        "subject_official_id": item.subject_official_id,
        "object_official_id": item.object_official_id,
        "subject_name": names.get(item.subject_official_id),
        "object_name": names.get(item.object_official_id),
        "relationship_type": item.relationship_type,
        "start_date": item.start_date,
        "end_date": item.end_date,
        "strength_score": float(item.strength_score),
        "confidence": float(item.confidence),
        "is_inferred": item.is_inferred,
        "evidence_summary": item.evidence_summary,
        "review_status": item.review_status,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }
