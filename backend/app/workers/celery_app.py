from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "senior_official_profile_analysis",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.crawl_tasks",
        "app.workers.analysis_tasks",
    ],
)

celery_app.conf.timezone = "Asia/Shanghai"
celery_app.conf.task_routes = {
    "app.workers.crawl_tasks.*": {"queue": "crawl"},
    "app.workers.analysis_tasks.*": {"queue": "analysis"},
}

