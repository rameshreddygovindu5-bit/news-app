"""
In-Process Job Scheduler using APScheduler.

Runs inside the FastAPI process — no Redis or Celery needed.
Jobs run in a background thread pool, won't block the API.

Usage (in main.py):
    from app.tasks.scheduler import start_scheduler, stop_scheduler
    @asynccontextmanager
    async def lifespan(app):
        start_scheduler()
        yield
        stop_scheduler()
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: BackgroundScheduler = None


def _run_scrape():
    from app.tasks.celery_app import scrape_all_sources
    try:
        scrape_all_sources()
    except Exception as e:
        logger.error(f"[SCHED] Scrape failed: {e}")


def _run_ai():
    from app.tasks.celery_app import process_ai_batch
    try:
        process_ai_batch()
    except Exception as e:
        logger.error(f"[SCHED] AI failed: {e}")


def _run_ranking():
    from app.tasks.celery_app import update_top_100_ranking
    try:
        update_top_100_ranking()
    except Exception as e:
        logger.error(f"[SCHED] Ranking failed: {e}")


def _run_social():
    from app.tasks.celery_app import post_to_social
    try:
        post_to_social()
    except Exception as e:
        logger.error(f"[SCHED] Social failed: {e}")


def _run_aws_sync():
    from app.tasks.celery_app import sync_to_aws
    try:
        sync_to_aws()
    except Exception as e:
        logger.error(f"[SCHED] AWS sync failed: {e}")


def _run_categories():
    from app.tasks.celery_app import update_category_counts
    try:
        update_category_counts()
    except Exception as e:
        logger.error(f"[SCHED] Categories failed: {e}")


def _run_cleanup():
    from app.tasks.celery_app import cleanup_old_articles
    try:
        cleanup_old_articles()
    except Exception as e:
        logger.error(f"[SCHED] Cleanup failed: {e}")


def start_scheduler():
    """Start the in-process scheduler. Called from FastAPI lifespan."""
    global _scheduler

    if not settings.SCHEDULER_ENABLED:
        logger.info("[SCHED] Scheduler disabled")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")

    # Parse interval from config — convert cron minute string to interval minutes
    def parse_interval(minute_str: str) -> int:
        """Convert '0,30' → 30, '5,35' → 30, '*/10' → 10"""
        minute_str = minute_str.strip()
        if minute_str.startswith("*/"):
            return int(minute_str[2:])
        parts = [int(x) for x in minute_str.split(",") if x.strip().isdigit()]
        if len(parts) >= 2:
            return parts[1] - parts[0]
        return 30  # default

    jobs = [
        ("scrape", settings.SCHEDULE_SCRAPE_ENABLED, settings.SCHEDULE_SCRAPE_MINUTES, _run_scrape),
        ("ai", settings.SCHEDULE_AI_ENABLED, settings.SCHEDULE_AI_MINUTES, _run_ai),
        ("ranking", settings.SCHEDULE_RANKING_ENABLED, settings.SCHEDULE_RANKING_MINUTES, _run_ranking),
        ("social", settings.SCHEDULE_SOCIAL_ENABLED, settings.SCHEDULE_SOCIAL_MINUTES, _run_social),
        ("aws_sync", settings.SCHEDULE_AWS_SYNC_ENABLED, settings.SCHEDULE_AWS_SYNC_MINUTES, _run_aws_sync),
        ("categories", settings.SCHEDULE_CATEGORY_COUNT_ENABLED, settings.SCHEDULE_CATEGORY_MINUTES, _run_categories),
        ("cleanup", settings.SCHEDULE_CLEANUP_ENABLED, settings.SCHEDULE_CLEANUP_MINUTES, _run_cleanup),
    ]

    for name, enabled, minutes_str, func in jobs:
        if enabled:
            interval = parse_interval(minutes_str)
            _scheduler.add_job(
                func, IntervalTrigger(minutes=interval),
                id=name, name=name, replace_existing=True,
                max_instances=1,  # Don't overlap
            )
            logger.info(f"[SCHED] ✓ {name}: every {interval} min")
        else:
            logger.info(f"[SCHED] ✗ {name}: disabled")

    _scheduler.start()
    logger.info(f"[SCHED] Scheduler started with {len(_scheduler.get_jobs())} jobs")


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHED] Scheduler stopped")


def get_scheduler_status() -> dict:
    """Get current scheduler status for admin API."""
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
