from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.db.models import (
    CareerEvent,
    CommitteeTerm,
    Location,
    Official,
    OfficialTermMembership,
    Organization,
    Relationship,
    RelationshipWeightItem,
    RelationshipWeightProfile,
)
from app.modules.relationships.scoring import (
    RelationshipWeight,
    calculate_overlap_days,
    score_relationship_edge,
)


GENERATED_RELATIONSHIP_TYPES = {
    "same_committee_term",
    "same_school",
    "same_organization_overlap",
    "same_location_overlap",
}


@dataclass
class RelationshipCandidate:
    subject_id: str
    object_id: str
    relationship_type: str
    strength_score: float
    confidence: float
    evidence_summary: str
    start_date: date | None = None
    end_date: date | None = None
    is_inferred: bool = True


def rebuild_generated_relationships(db: Session) -> dict[str, int]:
    default_profile = get_default_weight_profile(db)
    weights = get_weight_map(db, default_profile)
    candidates: dict[tuple[str, str, str], RelationshipCandidate] = {}

    db.query(Relationship).filter(
        Relationship.relationship_type.in_(GENERATED_RELATIONSHIP_TYPES),
        Relationship.is_inferred.is_(True),
    ).delete(synchronize_session=False)

    add_committee_relationships(db, candidates, weights)
    add_event_relationships(db, candidates, weights)

    for candidate in candidates.values():
        db.add(
            Relationship(
                subject_official_id=candidate.subject_id,
                object_official_id=candidate.object_id,
                relationship_type=candidate.relationship_type,
                start_date=candidate.start_date,
                end_date=candidate.end_date,
                strength_score=candidate.strength_score,
                confidence=candidate.confidence,
                is_inferred=candidate.is_inferred,
                evidence_summary=candidate.evidence_summary,
                weight_profile_id=default_profile.id if default_profile else None,
                review_status="verified",
            )
        )

    db.commit()
    return {
        "generated_relationships": len(candidates),
        "relationship_types": len(GENERATED_RELATIONSHIP_TYPES),
    }


def add_committee_relationships(
    db: Session,
    candidates: dict[tuple[str, str, str], RelationshipCandidate],
    weights: dict[str, RelationshipWeight],
) -> None:
    terms = db.query(CommitteeTerm).all()
    for term in terms:
        memberships = (
            db.query(OfficialTermMembership)
            .filter(OfficialTermMembership.term_id == term.id)
            .order_by(OfficialTermMembership.rank_order.asc().nulls_last())
            .all()
        )
        for index, left in enumerate(memberships):
            for right in memberships[index + 1 :]:
                left_id, right_id = ordered_pair(left.official_id, right.official_id)
                score = min(
                    weights["same_committee_term"].max_score,
                    weights["same_committee_term"].base_weight,
                )
                upsert_candidate(
                    candidates,
                    RelationshipCandidate(
                        subject_id=left_id,
                        object_id=right_id,
                        relationship_type="same_committee_term",
                        strength_score=score,
                        confidence=1.0,
                        is_inferred=False,
                        evidence_summary=f"同属{term.name}",
                    ),
                )


def add_event_relationships(
    db: Session,
    candidates: dict[tuple[str, str, str], RelationshipCandidate],
    weights: dict[str, RelationshipWeight],
) -> None:
    events = (
        db.query(CareerEvent)
        .filter(CareerEvent.deleted_at.is_(None), CareerEvent.review_status != "rejected")
        .all()
    )
    if not events:
        return

    org_names = {
        org.id: org.name
        for org in db.query(Organization)
        .filter(
            Organization.id.in_(
                {event.organization_id for event in events if event.organization_id}
            )
        )
        .all()
    }
    location_names = {
        loc.id: loc.name
        for loc in db.query(Location)
        .filter(Location.id.in_({event.location_id for event in events if event.location_id}))
        .all()
    }
    official_names = {
        official.id: official.name
        for official in db.query(Official)
        .filter(Official.id.in_({event.official_id for event in events}))
        .all()
    }

    for index, left in enumerate(events):
        for right in events[index + 1 :]:
            if left.official_id == right.official_id:
                continue

            if left.organization_id and left.organization_id == right.organization_id:
                add_organization_candidate(
                    left,
                    right,
                    org_names.get(left.organization_id, "同一机构"),
                    official_names,
                    candidates,
                    weights,
                )

            if left.location_id and left.location_id == right.location_id:
                add_location_candidate(
                    left,
                    right,
                    location_names.get(left.location_id, "同一地区"),
                    official_names,
                    candidates,
                    weights,
                )


def add_organization_candidate(
    left: CareerEvent,
    right: CareerEvent,
    organization_name: str,
    official_names: dict[str, str],
    candidates: dict[tuple[str, str, str], RelationshipCandidate],
    weights: dict[str, RelationshipWeight],
) -> None:
    if left.event_type == "education" and right.event_type == "education":
        relationship_type = "same_school"
        overlap_days = calculate_overlap_days(
            left.start_date,
            left.end_date,
            right.start_date,
            right.end_date,
        )
        score = weights[relationship_type].base_weight
        if overlap_days > 0:
            score = min(weights[relationship_type].max_score, score + 15)
        evidence = (
            f"{official_names.get(left.official_id, 'A')}与"
            f"{official_names.get(right.official_id, 'B')}均有{organization_name}学习经历"
        )
    else:
        overlap_days = calculate_overlap_days(left.start_date, left.end_date, right.start_date, right.end_date)
        if overlap_days <= 0:
            return
        relationship_type = "same_organization_overlap"
        score = score_relationship_edge(weights[relationship_type], overlap_days, "B", 0.85)
        evidence = (
            f"{official_names.get(left.official_id, 'A')}与"
            f"{official_names.get(right.official_id, 'B')}在{organization_name}任职时间重叠"
        )

    subject_id, object_id = ordered_pair(left.official_id, right.official_id)
    upsert_candidate(
        candidates,
        RelationshipCandidate(
            subject_id=subject_id,
            object_id=object_id,
            relationship_type=relationship_type,
            strength_score=score,
            confidence=0.85,
            evidence_summary=evidence,
            start_date=max_date(left.start_date, right.start_date),
            end_date=min_date(left.end_date, right.end_date),
        ),
    )


def add_location_candidate(
    left: CareerEvent,
    right: CareerEvent,
    location_name: str,
    official_names: dict[str, str],
    candidates: dict[tuple[str, str, str], RelationshipCandidate],
    weights: dict[str, RelationshipWeight],
) -> None:
    overlap_days = calculate_overlap_days(left.start_date, left.end_date, right.start_date, right.end_date)
    if overlap_days <= 0:
        return
    score = score_relationship_edge(weights["same_location_overlap"], overlap_days, "B", 0.8)
    subject_id, object_id = ordered_pair(left.official_id, right.official_id)
    upsert_candidate(
        candidates,
        RelationshipCandidate(
            subject_id=subject_id,
            object_id=object_id,
            relationship_type="same_location_overlap",
            strength_score=score,
            confidence=0.8,
            evidence_summary=(
                f"{official_names.get(left.official_id, 'A')}与"
                f"{official_names.get(right.official_id, 'B')}在{location_name}任职时间重叠"
            ),
            start_date=max_date(left.start_date, right.start_date),
            end_date=min_date(left.end_date, right.end_date),
        ),
    )


def upsert_candidate(
    candidates: dict[tuple[str, str, str], RelationshipCandidate],
    candidate: RelationshipCandidate,
) -> None:
    key = (candidate.subject_id, candidate.object_id, candidate.relationship_type)
    existing = candidates.get(key)
    if not existing or candidate.strength_score > existing.strength_score:
        candidates[key] = candidate


def get_default_weight_profile(db: Session) -> RelationshipWeightProfile | None:
    return (
        db.query(RelationshipWeightProfile)
        .filter(RelationshipWeightProfile.is_default.is_(True))
        .first()
    )


def get_weight_map(
    db: Session,
    profile: RelationshipWeightProfile | None,
) -> dict[str, RelationshipWeight]:
    defaults = {
        "same_committee_term": RelationshipWeight("same_committee_term", 10, 25, False),
        "same_school": RelationshipWeight("same_school", 25, 50, False),
        "same_organization_overlap": RelationshipWeight("same_organization_overlap", 60, 90, True),
        "same_location_overlap": RelationshipWeight("same_location_overlap", 45, 70, True),
    }
    if not profile:
        return defaults

    rows = db.query(RelationshipWeightItem).filter(RelationshipWeightItem.profile_id == profile.id).all()
    for row in rows:
        if row.relationship_type in defaults:
            defaults[row.relationship_type] = RelationshipWeight(
                relationship_type=row.relationship_type,
                base_weight=float(row.base_weight),
                max_score=float(row.max_score),
                time_decay_enabled=row.time_decay_enabled,
            )
    return defaults


def ordered_pair(left_id: str, right_id: str) -> tuple[str, str]:
    return (left_id, right_id) if left_id < right_id else (right_id, left_id)


def max_date(left: date | None, right: date | None) -> date | None:
    if left and right:
        return max(left, right)
    return left or right


def min_date(left: date | None, right: date | None) -> date | None:
    if left and right:
        return min(left, right)
    return left or right
