from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.analysis_tasks.rebuild_relationships")
def rebuild_relationships() -> dict[str, str]:
    # Relationship generation will consume career events in the analysis milestone.
    return {"status": "queued"}

