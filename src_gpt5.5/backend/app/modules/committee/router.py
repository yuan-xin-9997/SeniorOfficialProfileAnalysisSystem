import csv
from io import StringIO

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import CommitteeTerm, Official, OfficialTermMembership
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, require_admin
from app.modules.committee.schemas import (
    CommitteeImportRequest,
    CommitteeImportResult,
    CommitteeTermRead,
)

router = APIRouter()


@router.get("/terms", response_model=list[CommitteeTermRead])
def list_terms(
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CommitteeTerm]:
    return db.query(CommitteeTerm).order_by(CommitteeTerm.term_no.desc()).all()


@router.post("/import-members", response_model=CommitteeImportResult)
def import_members(
    payload: CommitteeImportRequest,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CommitteeImportResult:
    term = _ensure_term(db, payload)
    reader = csv.DictReader(StringIO(payload.csv_text.strip()))

    created_officials = 0
    updated_officials = 0
    memberships_upserted = 0
    skipped_rows = 0

    for index, row in enumerate(reader, start=1):
        name = (row.get("name") or row.get("姓名") or "").strip()
        if not name:
            skipped_rows += 1
            continue

        membership_type = normalize_membership_type(
            row.get("membership_type") or row.get("委员类型") or row.get("类型") or "member"
        )
        rank_order = parse_int(row.get("rank_order") or row.get("排序")) or index
        summary = (row.get("profile_summary") or row.get("简介") or "").strip() or None

        official = db.query(Official).filter(Official.name == name, Official.deleted_at.is_(None)).first()
        if official:
            if summary and not official.profile_summary:
                official.profile_summary = summary
                updated_officials += 1
        else:
            official = Official(
                name=name,
                birth_date_precision="unknown",
                profile_summary=summary,
                review_status="draft",
            )
            db.add(official)
            db.flush()
            created_officials += 1

        membership = (
            db.query(OfficialTermMembership)
            .filter(
                OfficialTermMembership.official_id == official.id,
                OfficialTermMembership.term_id == term.id,
            )
            .first()
        )
        if membership:
            membership.membership_type = membership_type
            membership.rank_order = rank_order
        else:
            db.add(
                OfficialTermMembership(
                    official_id=official.id,
                    term_id=term.id,
                    membership_type=membership_type,
                    rank_order=rank_order,
                )
            )
        memberships_upserted += 1

    db.commit()
    return CommitteeImportResult(
        term_id=term.id,
        created_officials=created_officials,
        updated_officials=updated_officials,
        memberships_upserted=memberships_upserted,
        skipped_rows=skipped_rows,
    )


def _ensure_term(db: Session, payload: CommitteeImportRequest) -> CommitteeTerm:
    term = db.query(CommitteeTerm).filter(CommitteeTerm.term_no == payload.term_no).first()
    if term:
        term.name = payload.term_name
        term.start_year = payload.start_year
        term.end_year = payload.end_year
        term.is_current = True
    else:
        term = CommitteeTerm(
            term_no=payload.term_no,
            name=payload.term_name,
            start_year=payload.start_year,
            end_year=payload.end_year,
            is_current=True,
        )
        db.add(term)
        db.flush()

    db.query(CommitteeTerm).filter(CommitteeTerm.id != term.id).update({"is_current": False})
    return term


def normalize_membership_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"alternate", "alternate_member", "候补", "候补委员"}:
        return "alternate_member"
    return "member"


def parse_int(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None

