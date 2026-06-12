from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import init_db
from app.modules.analysis.router import router as analysis_router
from app.modules.auth.router import router as auth_router
from app.modules.committee.router import router as committee_router
from app.modules.health.router import router as health_router
from app.modules.officials.router import router as officials_router
from app.modules.relationships.router import router as relationships_router
from app.modules.sources.router import router as sources_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api/health", tags=["health"])
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(committee_router, prefix="/api/committee", tags=["committee"])
    app.include_router(officials_router, prefix="/api/officials", tags=["officials"])
    app.include_router(sources_router, prefix="/api/sources", tags=["sources"])
    app.include_router(
        relationships_router,
        prefix="/api/relationships",
        tags=["relationships"],
    )
    app.include_router(analysis_router, prefix="/api/analysis", tags=["analysis"])

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()

    return app


app = create_app()
