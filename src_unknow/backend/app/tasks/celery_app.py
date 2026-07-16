from app.core.config import get_settings
from celery import Celery

settings = get_settings()

celery_app = Celery("sopas", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)

celery_app.autodiscover_tasks(["app.tasks"])

import app.tasks.scraper_tasks  # noqa: F401, E402
