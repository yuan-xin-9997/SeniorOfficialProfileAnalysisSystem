from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import success
from app.services.analysis.analysis_service import AnalysisService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/relationship")
async def relationship(
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    official_a: UUID = Query(...),
    official_b: UUID = Query(...),
):
    svc = AnalysisService(db)
    data = await svc.get_relationship(official_a, official_b)
    return success(data)


@router.get("/connections")
async def connections(
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    official_id: UUID = Query(...),
    min_strength: float = Query(0.3, ge=0, le=1),
):
    svc = AnalysisService(db)
    data = await svc.get_connections(official_id, min_strength)
    return success(data)


@router.get("/path")
async def path(
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_id: UUID = Query(..., alias="from"),
    to_id: UUID = Query(..., alias="to"),
    max_depth: int = Query(3, ge=1, le=5),
):
    svc = AnalysisService(db)
    data = await svc.get_path(from_id, to_id, max_depth)
    return success(data)


@router.post("/clustering")
async def clustering(
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AnalysisService(db)
    data = await svc.run_clustering()
    return success(data)


@router.get("/similarity")
async def similarity(
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    official_a: UUID = Query(...),
    official_b: UUID = Query(...),
):
    svc = AnalysisService(db)
    data = await svc.get_similarity(official_a, official_b)
    return success(data)


@router.get("/statistics")
async def statistics(
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AnalysisService(db)
    data = await svc.get_statistics()
    return success(data)
