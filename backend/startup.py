"""Initialize database on startup — always uses SQLite"""
import asyncio
import os
import sys

# Force SQLite before any imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./dataflow.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./dataflow.db"

sys.path.insert(0, os.path.dirname(__file__))


async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import text

    engine = create_async_engine(
        "sqlite+aiosqlite:///./dataflow.db",
        connect_args={"check_same_thread": False}
    )

    # Import all models so metadata is populated
    import app.models  # noqa: F401
    from app.db.base import Base

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created")

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        # Check if already seeded
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        if count > 0:
            print("✅ Already seeded, skipping")
            await engine.dispose()
            return

        from app.core.security import hash_password
        pwd_hash = hash_password("dataflow123")

        # Create org
        await db.execute(text("""
            INSERT INTO organizations (id, name, slug, description, is_active, created_at, updated_at)
            VALUES ('org-1', 'DataFlow Demo', 'dataflow-demo', 'Demo organization', 1, datetime('now'), datetime('now'))
        """))

        # Create user
        await db.execute(text("""
            INSERT INTO users (id, email, full_name, hashed_password, is_active, is_superuser, created_at, updated_at)
            VALUES ('user-1', 'shyam@dataflow.io', 'Shyam Patil', :pwd, 1, 1, datetime('now'), datetime('now'))
        """), {"pwd": pwd_hash})

        # Create member — uses joined_at not created_at
        await db.execute(text("""
            INSERT INTO organization_members (id, user_id, organization_id, role, joined_at)
            VALUES ('member-1', 'user-1', 'org-1', 'owner', datetime('now'))
        """))

        await db.commit()
        print("✅ Demo user seeded: shyam@dataflow.io / dataflow123")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
