from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.crawl_tasks.enqueue_weekly_crawl")
def enqueue_weekly_crawl() -> dict[str, str]:
    # The real crawler is wired in the crawl milestone; this placeholder keeps
    # scheduling and worker deployment testable from day one.
    return {"status": "scheduled"}

