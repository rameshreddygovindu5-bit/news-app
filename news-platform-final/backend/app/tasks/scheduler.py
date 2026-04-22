"""
In-Process Pipeline Scheduler v3
=================================
Runs the full news pipeline automatically using APScheduler BackgroundScheduler.
Schedule is read from .env via SCHEDULE_*_MINUTES settings (CronTrigger format).

Jobs registered:
  1. Scrape all sources     — SCHEDULE_SCRAPE_MINUTES   (default: 0,30)
  2. AI rephrase/categorize — SCHEDULE_AI_MINUTES       (default: */10)
  3. Update rankings        — SCHEDULE_RANKING_MINUTES  (default: */10)
  4. Update category counts — SCHEDULE_CATEGORY_MINUTES (default: */15)
  5. AWS sync               — SCHEDULE_AWS_SYNC_MINUTES (default: */5)
  6. Cleanup                — every 6 hours (fixed)

On startup: runs full pipeline once immediately (run_immediately=True).
Schedule is in sync with Celery Beat when both run concurrently.
"""

import time
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: BackgroundScheduler = None
_pipeline_lock = threading.Lock()


def _run_step(name, task_path, ignore_window: bool = False):
    """Import and run a specific task function with time window guard."""
    try:
        from datetime import datetime, timezone, timedelta
        now_utc = datetime.now(timezone.utc)
        now_ist_hour = (now_utc + timedelta(hours=5, minutes=30)).hour
        now_est_hour = (now_utc - timedelta(hours=5)).hour

        # Window check: removed to enable 24/7 automation
        pass

        logger.info(f"[SCHED] Running {name}...")
        import importlib
        mod_name, func_name = task_path.rsplit('.', 1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        
        # Pass ignore_window to the function if it's the scrape task
        if "scrape" in name.lower():
            result = func(ignore_window=ignore_window)
        else:
            result = func()
        logger.info(f"[SCHED] {name} done: {result}")
    except Exception as e:
        logger.error(f"[SCHED] {name} failed: {e}")


def _run_full_pipeline():
    """Master pipeline — runs all steps sequentially. Always ignores windows (manual restart)."""
    if not _pipeline_lock.acquire(blocking=False):
        logger.warning("[PIPELINE] Already running, skipping")
        return

    try:
        t0 = time.time()
        logger.info("=" * 55)
        logger.info("[PIPELINE] Starting automated news pipeline (Window Ignored)")
        logger.info("=" * 55)

        # CRITICAL STEP 0: Reset ALL stuck "processing" articles before doing anything
        try:
            from app.database import SyncSessionLocal
            from sqlalchemy import update as sa_update
            from app.models.models import NewsArticle as NA
            _db = SyncSessionLocal()
            stuck = _db.execute(
                sa_update(NA)
                .where(NA.ai_status.in_(["processing", "REWRITE_FAILED", "failed"]))
                .values(ai_status="pending", ai_error_count=0)
            )
            _db.commit()
            _db.close()
            if stuck.rowcount:
                logger.info(f"[PIPELINE] Reset {stuck.rowcount} stuck 'processing' → pending")
        except Exception as e:
            logger.warning(f"[PIPELINE] Stuck reset failed: {e}")

        steps = []

        # Main Pipeline Steps (ordered for maximum fresh content flow)
        steps.extend([
            ("Scrape",           "app.tasks.celery_app.scrape_all_sources"),
            ("AI Process",       "app.tasks.celery_app.process_ai_batch"),
            ("AI Process #2",    "app.tasks.celery_app.process_ai_batch"),  # second pass: catches any missed
            ("Ranking",          "app.tasks.celery_app.update_top_100_ranking"),
            ("Category Counts",  "app.tasks.celery_app.update_category_counts"),
        ])

        if settings.SCHEDULE_AWS_SYNC_ENABLED:
            steps.append(("AWS Sync", "app.tasks.celery_app.sync_to_aws"))

        if settings.SCHEDULE_SOCIAL_ENABLED:
            steps.append(("Social Post", "app.tasks.celery_app.post_to_social"))

        for i, (label, path_str) in enumerate(steps, 1):
            logger.info(f"[PIPELINE] Step {i}/{len(steps)}: {label}")
            _run_step(label, path_str, ignore_window=True)
            time.sleep(2)  # brief pause for DB commits to flush

        elapsed = round(time.time() - t0, 1)
        logger.info(f"[PIPELINE] Complete in {elapsed}s")
        logger.info("=" * 55)
    finally:
        _pipeline_lock.release()


def start_scheduler(run_immediately: bool = True, enable_intervals: bool = True):
    """Start the in-process scheduler. Batch Mode: run_immediately=True, enable_intervals=False."""
    global _scheduler

    if not settings.SCHEDULER_ENABLED:
        logger.info("[SCHED] Scheduler disabled")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")

    if enable_intervals:
        def _make_cron(minutes_str: str):
            """Build CronTrigger from .env minute string (e.g. '*/10', '0,30')."""
            return CronTrigger(minute=minutes_str, timezone="UTC")

        # Scraping — respects SCHEDULE_SCRAPE_MINUTES from .env
        if settings.SCHEDULE_SCRAPE_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("scrape", "app.tasks.celery_app.scrape_all_sources"),
                _make_cron(settings.SCHEDULE_SCRAPE_MINUTES),
                id="scrape_job", name="Scraping",
            )
            logger.info(f"[SCHED] ✓ Scraping: minute={settings.SCHEDULE_SCRAPE_MINUTES}")

        # AI Processing — respects SCHEDULE_AI_MINUTES from .env
        if settings.SCHEDULE_AI_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("ai", "app.tasks.celery_app.process_ai_batch"),
                _make_cron(settings.SCHEDULE_AI_MINUTES),
                id="ai_job", name="AI Processing",
            )
            logger.info(f"[SCHED] ✓ AI Process: minute={settings.SCHEDULE_AI_MINUTES}")

        # Ranking — respects SCHEDULE_RANKING_MINUTES from .env
        if settings.SCHEDULE_RANKING_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("ranking", "app.tasks.celery_app.update_top_100_ranking"),
                _make_cron(settings.SCHEDULE_RANKING_MINUTES),
                id="ranking_job", name="Ranking",
            )
            logger.info(f"[SCHED] ✓ Ranking: minute={settings.SCHEDULE_RANKING_MINUTES}")

        # Category counts — respects SCHEDULE_CATEGORY_MINUTES from .env
        if settings.SCHEDULE_CATEGORY_COUNT_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("cats", "app.tasks.celery_app.update_category_counts"),
                _make_cron(settings.SCHEDULE_CATEGORY_MINUTES),
                id="cats_job", name="Category Counts",
            )
            logger.info(f"[SCHED] ✓ Category counts: minute={settings.SCHEDULE_CATEGORY_MINUTES}")

        # AWS Sync — respects SCHEDULE_AWS_SYNC_MINUTES from .env
        if settings.SCHEDULE_AWS_SYNC_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("sync", "app.tasks.celery_app.sync_to_aws"),
                _make_cron(settings.SCHEDULE_AWS_SYNC_MINUTES),
                id="sync_job", name="AWS Sync",
            )
            logger.info(f"[SCHED] ✓ AWS Sync: minute={settings.SCHEDULE_AWS_SYNC_MINUTES}")

        # Cleanup — every 6 hours (fixed, not cron-per-minute)
        if settings.SCHEDULE_CLEANUP_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("cleanup", "app.tasks.celery_app.cleanup_old_articles"),
                IntervalTrigger(hours=6), id="cleanup_job", name="Cleanup",
            )
            logger.info("[SCHED] ✓ Cleanup: every 6 hours")
    else:
        logger.info("[SCHED] Running in BATCH MODE — Automatic intervals disabled")

    # Run full pipeline once at startup
    if run_immediately:
        _scheduler.add_job(
            _run_full_pipeline, 'date',
            id="startup_pipeline", name="Startup Pipeline",
            misfire_grace_time=300,
        )

    _scheduler.start()
    logger.info(f"[SCHED] Started — {len(_scheduler.get_jobs())} jobs registered")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHED] Stopped")


def get_scheduler_status() -> dict:
    if not _scheduler:
        return {"running": False, "jobs": []}
    return {
        "running": _scheduler.running,
        "jobs": [
            {"id": j.id, "name": j.name, "next_run": str(j.next_run_time),
             "trigger": str(j.trigger)}
            for j in _scheduler.get_jobs()
        ],
    }
