import os
import pathlib as _pathlib
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Always SQLite — ignore any injected DATABASE_URL from platform (Railway injects MySQL)
# base.py is at /app/app/db/base.py
# .parent = /app/app/db  → .parent.parent = /app/app  → .parent.parent.parent = /app
_DB_DIR = _pathlib.Path(__file__).resolve().parent.parent.parent
_DB_PATH = _DB_DIR / "dataflow.db"
SQLITE_URL = f"sqlite+aiosqlite:///{_DB_PATH}"

_DB_PATH_SYNC = str(_DB_PATH)
DATABASE_URL_SYNC = f"sqlite:///{_DB_PATH_SYNC}"

engine = create_async_engine(
    SQLITE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
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
