from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.models.scraper import ScraperLog, ScraperSource, ScraperTask
from app.models.user import User
from app.schemas.common import success
from app.tasks.scraper_tasks import run_scraper_task

router = APIRouter(prefix="/scraper", tags=["scraper"])


class TaskCreate(BaseModel):
    name: str
    source_id: UUID | None = None
    schedule_cron: str | None = None


class ScheduleUpdate(BaseModel):
    schedule_cron: str


@router.get("/sources")
async def list_sources(
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(ScraperSource).order_by(ScraperSource.name))
    sources = result.scalars().all()
    items = [
        {
            "id": str(s.id),
            "name": s.name,
            "base_url": s.base_url,
            "spider_class": s.spider_class,
            "status": s.status,
        }
        for s in sources
    ]
    return success(items)


@router.get("/tasks")
async def list_tasks(
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(ScraperTask).order_by(ScraperTask.created_at.desc()))
    tasks = result.scalars().all()
    return success(
        [
            {
                "id": str(t.id),
                "name": t.name,
                "status": t.status,
                "schedule_cron": t.schedule_cron,
                "celery_task_id": t.celery_task_id,
            }
            for t in tasks
        ]
    )


@router.post("/tasks")
async def create_task(
    body: TaskCreate,
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    task = ScraperTask(name=body.name, source_id=body.source_id, schedule_cron=body.schedule_cron)
    db.add(task)
    await db.flush()
    return success({"id": str(task.id), "name": task.name})


@router.post("/tasks/{task_id}/run")
async def run_task(
    task_id: UUID,
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    task = await db.get(ScraperTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    async_result = run_scraper_task.delay(str(task_id))
    task.status = "RUNNING"
    task.celery_task_id = async_result.id
    await db.flush()
    return success({"task_id": async_result.id, "status": "PENDING"})


@router.put("/tasks/{task_id}/schedule")
async def update_schedule(
    task_id: UUID,
    body: ScheduleUpdate,
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    task = await db.get(ScraperTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.schedule_cron = body.schedule_cron
    await db.flush()
    return success({"id": str(task.id), "schedule_cron": task.schedule_cron})


@router.get("/logs")
async def list_logs(
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
):
    result = await db.execute(select(ScraperLog).order_by(ScraperLog.started_at.desc()).limit(limit))
    logs = result.scalars().all()
    return success(
        [
            {
                "id": str(l.id),
                "task_id": str(l.task_id) if l.task_id else None,
                "status": l.status,
                "total": l.total,
                "updated_count": l.updated_count,
                "failed_count": l.failed_count,
                "message": l.message,
                "started_at": l.started_at.isoformat() if l.started_at else None,
                "finished_at": l.finished_at.isoformat() if l.finished_at else None,
            }
            for l in logs
        ]
    )
