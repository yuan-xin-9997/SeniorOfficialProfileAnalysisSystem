import uvicorn

from app.core.config import settings
from app.core.logging import build_log_config


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        log_config=build_log_config(
            settings.LOG_DIR,
            settings.LOG_LEVEL,
            settings.LOG_RETENTION_DAYS,
        ),
    )
