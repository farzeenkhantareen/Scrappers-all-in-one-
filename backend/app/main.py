"""
FastAPI main application entry point.
Configures CORS, WebSocket, routers, OpenAPI docs, startup/shutdown hooks.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.job_store import job_store

import sys
import asyncio

if sys.platform == "win32":
    try:
        asyncio.WindowsSelectorEventLoopPolicy = asyncio.WindowsProactorEventLoopPolicy
    except Exception:
        pass
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # ── Startup ──
    import asyncio
    import sys
    loop = asyncio.get_running_loop()
    print(f"--- STARTUP: RUNNING EVENT LOOP TYPE: {type(loop)} ---", flush=True)
    print(f"--- STARTUP: RUNNING LOOP POLICY: {type(asyncio.get_event_loop_policy())} ---", flush=True)
    print("Initializing database...", flush=True)
    await init_db()
    print("Database ready.", flush=True)
    yield  # Application runs
    logger.info("Shutdown complete.")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Scrappers Dashboard API",
    description="Multi-platform business data scraper API with real-time job tracking.",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
from app.routers import scrape, jobs, results, exports, logs, ai

app.include_router(scrape.router, prefix="/api/scrape", tags=["Scrapers"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(results.router, prefix="/api/results", tags=["Results"])
app.include_router(exports.router, prefix="/api/exports", tags=["Exports"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Assistant"])


# ── WebSocket endpoint ────────────────────────────────────────────────────────
@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    Connect to receive real-time progress and log events for a job.
    Messages are JSON with a 'type' field: 'progress' | 'log' | 'status'.
    """
    await websocket.accept()
    logger.info(f"WS connected: job={job_id}")

    # Callback that sends data down the websocket
    async def send_ws_data(data: dict):
        try:
            await websocket.send_json(data)
        except Exception:
            pass

    # Send current state immediately on connect
    job = job_store.get(job_id)
    if job:
        await send_ws_data({**job, "type": "status"})
        # Send existing logs
        logs = job_store.get_logs(job_id, limit=100)
        for log in reversed(logs):
            await send_ws_data({"type": "log", **log})

    # Register the callback with the job_store
    job_store.register_ws(job_id, send_ws_data)

    try:
        while True:
            # Keep connection alive by waiting for client messages/pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WS disconnected: job={job_id}")
    finally:
        job_store.unregister_ws(job_id, send_ws_data)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse({"message": "Scrappers Dashboard API. See /api/docs"})
