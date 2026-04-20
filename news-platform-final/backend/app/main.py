"""
News Aggregation Platform — FastAPI Application
===============================================
Startup sequence (lifespan):
  1. create_tables()  — auto-create all DB tables + seed defaults if missing
  2. start_scheduler() — start in-process APScheduler (fallback when no Celery Beat)
  3. CORS configured from settings.CORS_ORIGINS
  4. All API routers registered

Production: run Celery Worker + Celery Beat for proper async scheduling.
Development: single-process mode works fine — APScheduler runs in-process.
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import create_tables
from app.api import all_routers

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{'═' * 55}")
    logger.info(f"  {settings.APP_NAME}  v{settings.APP_VERSION}")
    logger.info(f"{'═' * 55}")

    # 1. Ensure all DB tables exist and defaults are seeded
    try:
        await create_tables()
        # Clean up any stuck 'RUNNING' jobs from previous crashes
        from app.database import SyncSessionLocal
        from app.models.models import JobExecutionLog
        from sqlalchemy import update, text
        db = SyncSessionLocal()
        try:
            db.execute(update(JobExecutionLog).where(JobExecutionLog.status == "RUNNING").values(
                status="FAILED", 
                error_summary="Terminated due to application restart"
            ))
            db.commit()
            logger.info("[DB] Cleaned up stuck 'RUNNING' jobs")
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"[DB] Table creation/cleanup failed: {exc}")
        logger.error("[DB] Check DATABASE_URL in .env — continuing anyway")

    # 2. Start in-process scheduler (ONLY on local dev)
    # On AWS/Production, the local environment pushes data, so the server
    # should remain passive to save resources.
    if settings.IS_LOCAL_DEV:
        try:
            from app.tasks.scheduler import start_scheduler
            scheduler = start_scheduler(run_immediately=True, enable_intervals=True)
            app.state.scheduler = scheduler
        except Exception as exc:
            logger.warning(f"[SCHEDULER] Could not start in-process scheduler: {exc}")
    else:
        logger.info("[SCHEDULER] Disabled (Production Mode — passive server)")

    yield

    # Shutdown
    try:
        if settings.IS_LOCAL_DEV:
            from app.tasks.scheduler import stop_scheduler as _real_stop
            _real_stop()
    except Exception:
        pass
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered news aggregation — "
        "scrape → translate → rephrase → Telugu → categorise → rank → AWS sync."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — merge .env list with hardcoded dev origins
_cors_origins = list(
    set(settings.CORS_ORIGINS + [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
        "http://localhost:3003", "http://127.0.0.1:3003",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ])
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

for router in all_routers:
    app.include_router(router)

# ── Static file serving for uploaded images ───────────────────────────
_upload_dir = Path(settings.UPLOAD_DIR)
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_upload_dir)), name="uploads")


@app.get("/", tags=["Core"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "mode": "local" if settings.IS_LOCAL_DEV else "production",
        "aws_sync": settings.IS_LOCAL_DEV and settings.SCHEDULE_AWS_SYNC_ENABLED,
        "docs": "/docs",
    }


@app.get("/health", tags=["Core"])
async def health():
    """Health-check for Docker HEALTHCHECK and load-balancers."""
    return {"status": "healthy", "version": settings.APP_VERSION}
