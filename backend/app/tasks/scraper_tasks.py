import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.scraper import ScraperLog, ScraperTask
from app.tasks.celery_app import celery_app


@celery_app.task(name="scraper.run_task")
def run_scraper_task(task_id: str) -> dict:
    return asyncio.run(_run_scraper_async(task_id))


async def _run_scraper_async(task_id: str) -> dict:
    from app.services.scraper.orchestrator import ScraperOrchestrator

    async with AsyncSessionLocal() as session:
        task = await session.get(ScraperTask, UUID(task_id))
        if task is None:
            return {"error": "task not found"}
        log = ScraperLog(task_id=task.id, status="RUNNING")
        session.add(log)
        await session.commit()
        try:
            orchestrator = ScraperOrchestrator(session)
            result = await orchestrator.run(task)
            log.status = "SUCCESS"
            log.total = result.get("total", 0)
            log.updated_count = result.get("updated", 0)
            log.failed_count = result.get("failed", 0)
            log.message = result.get("message", "completed")
            task.status = "IDLE"
        except Exception as exc:
            log.status = "FAILURE"
            log.message = str(exc)
            task.status = "FAILED"
            result = {"error": str(exc)}
        log.finished_at = datetime.now(timezone.utc)
        await session.commit()
        return result
