import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.base import get_db
from app.api.v1.routes import (
    auth, datasets, pipelines, runs, analytics,
    reports, alerts, team, api_keys, activity, overview, ws
)

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # Redis websocket relay — silently skip if unavailable
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
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
async def init_endpoint(db: AsyncSession = Depends(get_db)):
    """Re-seed the database if empty"""
    from app.core.security import hash_password
    result = await db.execute(text("SELECT COUNT(*) FROM users"))
    count = result.scalar()
    if count > 0:
        return {"status": "already seeded", "users": count}
    pwd = hash_password("dataflow123")
    await db.execute(text("INSERT INTO organizations (id,name,slug,description,is_active,created_at,updated_at) VALUES ('org-1','DataFlow Demo','dataflow-demo','Demo',1,datetime('now'),datetime('now'))"))
    await db.execute(text("INSERT INTO users (id,email,full_name,hashed_password,is_active,is_superuser,created_at,updated_at) VALUES ('user-1','shyam@dataflow.io','Shyam Patil',:pwd,1,1,datetime('now'),datetime('now'))"), {"pwd": pwd})
    await db.execute(text("INSERT INTO organization_members (id,user_id,organization_id,role,joined_at) VALUES ('member-1','user-1','org-1','owner',datetime('now'))"))
    return {"status": "seeded", "email": "shyam@dataflow.io", "password": "dataflow123"}


# ── Serve React frontend static files ─────────────────────────────────────────
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))

if os.path.isdir(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index = os.path.join(STATIC_DIR, "index.html")
        return FileResponse(index)
else:
    @app.get("/")
    async def root():
        return {"name": settings.APP_NAME, "version": settings.VERSION, "docs": "/docs"}
