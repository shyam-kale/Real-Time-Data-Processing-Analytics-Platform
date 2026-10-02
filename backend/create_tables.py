"""Run once to create all tables in SQLite."""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.base import engine, Base
import app.models  # noqa – registers all models


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created in dataflow.db")
    await engine.dispose()


asyncio.run(main())
