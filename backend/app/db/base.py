import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _get_database_url() -> str:
    """Always use SQLite. Ignore any MySQL/Postgres URL from environment."""
    url = os.environ.get("DATABASE_URL", "")
    # If it's a MySQL or Postgres URL, ignore it and use SQLite
    if url.startswith("mysql") or url.startswith("postgres"):
        return "sqlite+aiosqlite:///./dataflow.db"
    if url.startswith("sqlite"):
        return url
    return "sqlite+aiosqlite:///./dataflow.db"


DATABASE_URL = _get_database_url()
IS_SQLITE = "sqlite" in DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
