from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, engine
from app.core.neo4j_client import check_neo4j, close_neo4j_driver, get_neo4j_driver
from app.core.redis_client import check_redis, close_redis
from app.core.security import hash_password
from app.core.database import Base
from app.models.scraper import ScraperSource
from app.models.user import User
from app.schemas.common import success


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield
    await close_neo4j_driver()
    await close_redis()
    await engine.dispose()


async def init_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        settings = get_settings()
        result = await session.execute(select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME))
        if result.scalar_one_or_none() is None:
            session.add(
                User(
                    username=settings.DEFAULT_ADMIN_USERNAME,
                    password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                    role="admin",
                )
            )
        result = await session.execute(select(ScraperSource))
        if not result.scalars().first():
            session.add_all(
                [
                    ScraperSource(
                        name="人民网-领导人资料库",
                        base_url="https://www.people.com.cn",
                        spider_class="PeopleSpider",
                    ),
                    ScraperSource(
                        name="新华网-领导人资料",
                        base_url="https://www.xinhuanet.com",
                        spider_class="XinhuaSpider",
                    ),
                    ScraperSource(
                        name="中国政府网",
                        base_url="https://www.gov.cn",
                        spider_class="GovSpider",
                    ),
                ]
            )
        await session.commit()
    driver = get_neo4j_driver()
    async with driver.session() as session:
        await session.run("CREATE INDEX official_id IF NOT EXISTS FOR (o:Official) ON (o.id)")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health")
    async def health():
        return success({"status": "ok"})

    @app.get("/health/ready")
    async def ready():
        pg_ok = False
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
                pg_ok = True
        except Exception:
            pg_ok = False
        neo4j_ok = await check_neo4j()
        redis_ok = await check_redis()
        status = pg_ok and neo4j_ok and redis_ok
        return success(
            {"postgres": pg_ok, "neo4j": neo4j_ok, "redis": redis_ok, "ready": status},
            message="ready" if status else "degraded",
            code=200 if status else 503,
        )

    return app


app = create_app()
