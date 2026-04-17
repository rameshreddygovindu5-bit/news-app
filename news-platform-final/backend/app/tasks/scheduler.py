"""
In-Process Pipeline Scheduler v2
=================================
Runs the full news pipeline automatically:
  1. Scrape all sources (every 20 min)
  2. AI rephrase/categorize (every 10 min — more frequent to clear backlog)  
  3. Update rankings (every 20 min)
  4. Update category counts (every 20 min)
  5. AWS sync (every 30 min)
  6. Social posting (every 30 min)
  7. Cleanup (every 6 hours)

On startup: runs full pipeline once immediately.
"""

import time
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
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

        # Window check: only block if not a "force" or "ignore_window" run
        if not ignore_window and not (5 <= now_ist_hour < 21):
            if "scrape" in name.lower() and "google" in name.lower() and (5 <= now_est_hour < 21):
                pass
            else:
                logger.info(f"[SCHED] Task {name} skipped: Outside active 5AM-9PM IST window")
                return

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

        steps = []
        
        # 1. AWS Sync - Run first to clear backlog immediately on startup
        if settings.SCHEDULE_AWS_SYNC_ENABLED:
            steps.append(("AWS Sync", "app.tasks.celery_app.sync_to_aws"))

        # 2. Main Pipeline Steps
        steps.extend([
            ("Scrape", "app.tasks.celery_app.scrape_all_sources"),
            ("AI Process", "app.tasks.celery_app.process_ai_batch"),
            ("Ranking", "app.tasks.celery_app.update_top_100_ranking"),
            ("Category Counts", "app.tasks.celery_app.update_category_counts"),
        ])
        
        if settings.SCHEDULE_SOCIAL_ENABLED:
            steps.append(("Social Post", "app.tasks.celery_app.post_to_social"))

        for i, (label, path) in enumerate(steps, 1):
            logger.info(f"[PIPELINE] Step {i}/{len(steps)}: {label}")
            _run_step(label, path, ignore_window=True)
            time.sleep(2)

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
        # Scraping — every 20 min
        if settings.SCHEDULE_SCRAPE_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("scrape", "app.tasks.celery_app.scrape_all_sources"),
                IntervalTrigger(minutes=20), id="scrape_job", name="Scraping",
            )
            logger.info("[SCHED] ✓ Scraping: every 20 min")

        # AI Processing — every 10 min
        if settings.SCHEDULE_AI_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("ai", "app.tasks.celery_app.process_ai_batch"),
                IntervalTrigger(minutes=10), id="ai_job", name="AI Processing",
            )
            logger.info("[SCHED] ✓ AI Process: every 10 min")

        # Ranking — every 20 min
        if settings.SCHEDULE_RANKING_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("ranking", "app.tasks.celery_app.update_top_100_ranking"),
                IntervalTrigger(minutes=20), id="ranking_job", name="Ranking",
            )
            logger.info("[SCHED] ✓ Ranking: every 20 min")

        # Category counts — every 20 min
        if settings.SCHEDULE_CATEGORY_COUNT_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("cats", "app.tasks.celery_app.update_category_counts"),
                IntervalTrigger(minutes=20), id="cats_job", name="Category Counts",
            )
            logger.info("[SCHED] ✓ Category counts: every 20 min")

        # AWS Sync — every 30 min
        if settings.SCHEDULE_AWS_SYNC_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("sync", "app.tasks.celery_app.sync_to_aws"),
                IntervalTrigger(minutes=30), id="sync_job", name="AWS Sync",
            )
            logger.info("[SCHED] ✓ AWS Sync: every 30 min")

        # Cleanup — every 6 hours
        if settings.SCHEDULE_CLEANUP_ENABLED:
            _scheduler.add_job(
                lambda: _run_step("cleanup", "app.tasks.celery_app.cleanup_old_articles"),
                IntervalTrigger(hours=6), id="cleanup_job", name="Cleanup",
            )
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
    logger.info(f"[SCHED] Started — {len(_scheduler.get_jobs())} jobs")


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
