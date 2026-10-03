from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "DataFlow"
    APP_ENV: str = "production"
    DEBUG: bool = False
    VERSION: str = "1.0.0"

    SECRET_KEY: str = "dev-secret-key-change-in-production-aabbcc"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7   # 7 days for demo
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Always SQLite — hardcoded, not from env
    DATABASE_URL: str = "sqlite+aiosqlite:///./dataflow.db"
    DATABASE_URL_SYNC: str = "sqlite:///./dataflow.db"

    REDIS_URL: str = "redis://localhost:6379/0"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,https://real-time-data-processing-analytics-platform-production-8c61.up.railway.app"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 500

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return True


settings = Settings()
