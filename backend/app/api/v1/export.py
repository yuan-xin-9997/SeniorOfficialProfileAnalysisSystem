import csv
import io
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.official import CareerEntry, Official
from app.models.user import User
from app.schemas.common import success
from app.schemas.official import OfficialDetail

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/officials")
async def export_officials(
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    fmt: str = Query("json", pattern="^(json|csv)$"),
):
    result = await db.execute(
        select(Official).options(
            selectinload(Official.career_entries).selectinload(CareerEntry.education),
            selectinload(Official.career_entries).selectinload(CareerEntry.political_career),
        )
    )
    officials = result.scalars().all()
    data = [OfficialDetail.model_validate(o).model_dump(mode="json") for o in officials]

    if fmt == "json":
        content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=officials.json"},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "name", "birth_date", "birth_place", "committee_term", "status", "current_position"]
    )
    for o in officials:
        writer.writerow(
            [str(o.id), o.name, o.birth_date, o.birth_place, o.committee_term, o.status, o.current_position or ""]
        )
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=officials.csv"},
    )


@router.get("/analysis/{official_id}")
async def export_analysis(
    official_id: UUID,
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.services.analysis.analysis_service import AnalysisService

    svc = AnalysisService(db)
    rel = await svc.get_connections(official_id, 0.3)
    return success(rel)
