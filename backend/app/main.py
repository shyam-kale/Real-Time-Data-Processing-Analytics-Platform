import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.v1.routes import (
    auth, datasets, pipelines, runs, analytics,
    reports, alerts, team, api_keys, activity, overview, ws
)

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create upload dir
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Start Redis pub/sub relay (silently fails if Redis unavailable)
    from app.websockets.manager import redis_subscriber
    task = asyncio.create_task(redis_subscriber())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="DataFlow API",
    description="Data ingestion, processing, quality, and pipeline management",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for unhandled exceptions. FastAPI's CORSMiddleware does not
    add CORS headers to 500 responses, which masks the real error in the
    browser. This handler logs the error and returns a JSON 500 with the
    CORS origin header so the browser can read the actual error message.
    """
    import logging
    import traceback
    logger = logging.getLogger("app")
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())

    origin = request.headers.get("origin", "")
    allowed = settings.allowed_origins_list
    headers = {}
    if origin in allowed:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
        headers=headers,
    )

API = "/api/v1"
app.include_router(auth.router,     prefix=API)
app.include_router(overview.router, prefix=API)
app.include_router(datasets.router, prefix=API)
app.include_router(pipelines.router,prefix=API)
app.include_router(runs.router,     prefix=API)
app.include_router(analytics.router,prefix=API)
app.include_router(reports.router,  prefix=API)
app.include_router(alerts.router,   prefix=API)
app.include_router(team.router,     prefix=API)
app.include_router(api_keys.router, prefix=API)
app.include_router(activity.router, prefix=API)
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "version": settings.VERSION, "docs": "/docs"}
