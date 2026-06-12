from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Senior Official Profile Analysis System"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "dev"
    API_PREFIX: str = "/api"

    DATABASE_URL: str = "sqlite:///./dev.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    DEFAULT_CRAWL_CRON: str = "0 3 * * 1"
    RAW_DOCS_DIR: Path = Path("./data/raw-docs")

    LLM_PROVIDER: str = "disabled"
    LLM_API_KEY: str | None = None
    LLM_DAILY_LIMIT: int = 200

    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_PASSWORD: str = "admin123"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

