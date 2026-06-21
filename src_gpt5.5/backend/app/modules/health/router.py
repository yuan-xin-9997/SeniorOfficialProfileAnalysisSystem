from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }

