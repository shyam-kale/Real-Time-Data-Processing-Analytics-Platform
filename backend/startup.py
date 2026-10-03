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
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created")
        
        # Seed data using direct SQL (no module import needed)
        Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with Session() as db:
            from app.core.security import hash_password
            from sqlalchemy import text
            
            # Create org
            await db.execute(text("""
                INSERT OR IGNORE INTO organizations (id, name, slug, description, is_active, created_at, updated_at)
                VALUES ('org-1', 'DataFlow Demo', 'dataflow-demo', 'Demo organization', 1, datetime('now'), datetime('now'))
            """))
            
            # Create user
            pwd_hash = hash_password("dataflow123")
            await db.execute(text("""
                INSERT OR IGNORE INTO users (id, email, full_name, hashed_password, is_active, is_superuser, created_at, updated_at)
                VALUES ('user-1', 'shyam@dataflow.io', 'Shyam Patil', :pwd, 1, 1, datetime('now'), datetime('now'))
            """), {"pwd": pwd_hash})
            
            # Create member
            await db.execute(text("""
                INSERT OR IGNORE INTO members (id, user_id, organization_id, role, created_at)
                VALUES ('member-1', 'user-1', 'org-1', 'owner', datetime('now'))
            """))
            
            await db.commit()
        
        print("✅ Database seeded with demo user")
        
    except Exception as e:
        print(f"⚠️ Database init warning: {e}")
        # Don't fail startup, just warn
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

