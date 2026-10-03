import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.v1.routes import (
    auth, datasets, pipelines, runs, analytics,
    reports, alerts, team, api_keys, activity, overview, ws
)

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Initialize database tables
    try:
        from app.db.base import init_db
        asyncio.create_task(init_db())
    except Exception as e:
        print(f"Warning: Could not initialize DB: {e}")

    # Start Redis pub/sub relay (silently fails if Redis unavailable)
    try:
        from app.websockets.manager import redis_subscriber
        task = asyncio.create_task(redis_subscriber())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    except Exception:
        yield


app = FastAPI(
    title="DataFlow API",
    description="Data ingestion, processing, quality, and pipeline management",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow all origins in dev, restrict in production via env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ─────────────────────────────────────────────────────────────────
API = "/api/v1"
app.include_router(auth.router,      prefix=API)
app.include_router(overview.router,  prefix=API)
app.include_router(datasets.router,  prefix=API)
app.include_router(pipelines.router, prefix=API)
app.include_router(runs.router,      prefix=API)
app.include_router(analytics.router, prefix=API)
app.include_router(reports.router,   prefix=API)
app.include_router(alerts.router,    prefix=API)
app.include_router(team.router,      prefix=API)
app.include_router(api_keys.router,  prefix=API)
app.include_router(activity.router,  prefix=API)
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}


@app.get("/api/v1/init")
async def init_db(db: AsyncSession = Depends(get_db)):
    """One-time initialization — creates tables and seed user"""
    from sqlalchemy import text
    from app.core.security import hash_password
    try:
        async with db.begin():
            # Create org
            await db.execute(text("""
                INSERT OR IGNORE INTO organizations (id, name, slug, description, is_active, created_at, updated_at)
                VALUES ('org-1', 'DataFlow Demo', 'dataflow-demo', 'Demo organization', 1, datetime('now'), datetime('now'))
            """))
            # Create user
            await db.execute(text("""
                INSERT OR IGNORE INTO users (id, email, full_name, hashed_password, is_active, is_superuser, created_at, updated_at)
                VALUES ('user-1', 'shyam@dataflow.io', 'Shyam Patil', :pwd, 1, 1, datetime('now'), datetime('now'))
            """), {"pwd": hash_password("dataflow123")})
            # Create member
            await db.execute(text("""
                INSERT OR IGNORE INTO organization_members (id, user_id, organization_id, role, created_at)
                VALUES ('member-1', 'user-1', 'org-1', 'owner', datetime('now'))
            """))
        return {"status": "Database initialized", "email": "shyam@dataflow.io", "password": "dataflow123"}
    except Exception as e:
        return {"error": str(e)}


# ── Serve React frontend static files ─────────────────────────────────────────
# Only mount if the static folder exists (production build)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
STATIC_DIR = os.path.abspath(STATIC_DIR)

if os.path.isdir(STATIC_DIR):
    # Serve assets (JS, CSS, images) from /assets
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    # Serve everything else as the React SPA (catch-all)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Let API and docs routes through
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return {"error": "Frontend not built"}
else:
    # Development mode — no static files, just API
    @app.get("/")
    async def root():
        return {"name": settings.APP_NAME, "version": settings.VERSION, "docs": "/docs"}
