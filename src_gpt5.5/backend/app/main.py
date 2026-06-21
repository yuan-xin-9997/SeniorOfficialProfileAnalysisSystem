from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

    frontend_dist = settings.FRONTEND_DIST_DIR.resolve()
    assets_dir = frontend_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{path:path}", include_in_schema=False)
    def serve_frontend(path: str) -> FileResponse:
        requested = (frontend_dist / path).resolve()
        if path and requested.is_file() and frontend_dist.resolve() in requested.parents:
            return FileResponse(requested)
        index_file = frontend_dist / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        return FileResponse(Path(__file__).resolve().parent / "static-missing.html", status_code=503)

    return app


app = create_app()
