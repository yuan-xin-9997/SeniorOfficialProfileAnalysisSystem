from fastapi import APIRouter

from app.api.v1 import analysis, auth, export, officials, scraper, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(officials.router)
api_router.include_router(scraper.router)
api_router.include_router(analysis.router)
api_router.include_router(export.router)
