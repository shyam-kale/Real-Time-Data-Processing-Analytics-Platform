"""Initialize database on Railway startup"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

async def main():
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./dataflow.db")
    os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./dataflow.db")
    
    try:
        from app.db.base import Base, engine
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
        from app.seed import seed_data
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Seed data
        Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with Session() as db:
            await seed_data(db)
        
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database init failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
