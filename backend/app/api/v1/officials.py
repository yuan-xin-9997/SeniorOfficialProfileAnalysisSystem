from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.official import CareerEntry, Official
from app.models.user import User
from app.schemas.common import success
from app.schemas.official import CareerEntryOut, OfficialCreate, OfficialDetail, OfficialOut, OfficialUpdate
from app.services.official_service import OfficialService

router = APIRouter(prefix="/officials", tags=["officials"])


def _to_out(o: Official) -> dict:
    return OfficialOut.model_validate(o).model_dump()


def _to_detail(o: Official) -> dict:
    return OfficialDetail.model_validate(o).model_dump()


@router.get("")
async def list_officials(
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str | None = None,
    committee_term: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Official)
    if name:
        query = query.where(Official.name.ilike(f"%{name}%"))
    if committee_term:
        query = query.where(Official.committee_term == committee_term)
    if status:
        query = query.where(Official.status == status)
    count_query = select(func.count()).select_from(Official)
    if name:
        count_query = count_query.where(Official.name.ilike(f"%{name}%"))
    if committee_term:
        count_query = count_query.where(Official.committee_term == committee_term)
    if status:
        count_query = count_query.where(Official.status == status)
    total = await db.scalar(count_query)
    result = await db.execute(
        query.order_by(Official.name).offset((page - 1) * page_size).limit(page_size)
    )
    items = [_to_out(o) for o in result.scalars().all()]
    return success({"items": items, "total": total or 0, "page": page, "page_size": page_size})


@router.get("/{official_id}")
async def get_official(
    official_id: UUID,
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = OfficialService(db)
    official = await svc.get_by_id(official_id)
    if official is None:
        raise HTTPException(status_code=404, detail="Official not found")
    return success(_to_detail(official))


@router.post("")
async def create_official(
    body: OfficialCreate,
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = OfficialService(db)
    official = await svc.create(body)
    official = await svc.get_by_id(official.id)
    return success(_to_detail(official), message="created")


@router.put("/{official_id}")
async def update_official(
    official_id: UUID,
    body: OfficialUpdate,
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = OfficialService(db)
    official = await svc.get_by_id(official_id)
    if official is None:
        raise HTTPException(status_code=404, detail="Official not found")
    official = await svc.update(official, body)
    official = await svc.get_by_id(official.id)
    return success(_to_detail(official))


@router.delete("/{official_id}")
async def delete_official(
    official_id: UUID,
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = OfficialService(db)
    official = await svc.get_by_id(official_id)
    if official is None:
        raise HTTPException(status_code=404, detail="Official not found")
    await svc.delete(official)
    return success(message="deleted")


@router.get("/{official_id}/career")
async def get_career(
    official_id: UUID,
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(CareerEntry)
        .where(CareerEntry.official_id == official_id)
        .options(
            selectinload(CareerEntry.education),
            selectinload(CareerEntry.political_career),
        )
        .order_by(CareerEntry.start_year)
    )
    entries = result.scalars().all()
    return success([CareerEntryOut.model_validate(e).model_dump() for e in entries])
