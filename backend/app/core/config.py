import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


def _safe_db_url(url: str, sync: bool = False) -> str:
    """Return SQLite URL if MySQL/Postgres injected by platform."""
    if url.startswith("mysql") or url.startswith("postgres"):
        return "sqlite:///./dataflow.db" if sync else "sqlite+aiosqlite:///./dataflow.db"
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "DataFlow"
    APP_ENV: str = "development"
    DEBUG: bool = False
    VERSION: str = "1.0.0"

    SECRET_KEY: str = "dev-secret-key-change-in-production-aabbcc"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "sqlite+aiosqlite:///./dataflow.db"
    DATABASE_URL_SYNC: str = "sqlite:///./dataflow.db"

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,https://real-time-data-processing-analytics-platform-production-8c61.up.railway.app"

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 500

    @property
    def safe_database_url(self) -> str:
        return _safe_db_url(self.DATABASE_URL)

    @property
    def safe_database_url_sync(self) -> str:
        return _safe_db_url(self.DATABASE_URL_SYNC, sync=True)

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.safe_database_url


settings = Settings()
