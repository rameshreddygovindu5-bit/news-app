"""
In-Process Pipeline Scheduler.

Runs a full news pipeline every 30 minutes:
  Minute 0:  Scrape all sources
  Minute +5: AI rephrase/categorize
  Minute +10: Update rankings
  Minute +15: AWS sync + categories
  Minute +20: Social posting

All steps run sequentially inside a single pipeline job.
No Redis/Celery needed — runs in a background thread inside FastAPI.
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


def _run_full_pipeline():
    """The master pipeline — runs all steps sequentially."""
    if not _pipeline_lock.acquire(blocking=False):
        logger.warning("[PIPELINE] Already running, skipping this cycle")
        return

    try:
        logger.info("=" * 60)
        logger.info("[PIPELINE] Starting automated news pipeline")
        logger.info("=" * 60)
        t0 = time.time()

        # Step 1: Scrape all enabled sources
        logger.info("[PIPELINE] Step 1/6: Scraping all sources...")
        try:
            from app.tasks.celery_app import scrape_all_sources
            result = scrape_all_sources()
            logger.info(f"[PIPELINE] Scrape done: {result}")
        except Exception as e:
            logger.error(f"[PIPELINE] Scrape failed: {e}")

        # Step 2: AI rephrase + categorize (flag N → A)
        logger.info("[PIPELINE] Step 2/6: AI processing...")
        try:
            from app.tasks.celery_app import process_ai_batch
            result = process_ai_batch()
            logger.info(f"[PIPELINE] AI done: {result}")
        except Exception as e:
            logger.error(f"[PIPELINE] AI failed: {e}")

        # Step 3: Update rankings (flag A → Y for top articles)
        logger.info("[PIPELINE] Step 3/6: Updating rankings...")
        try:
            from app.tasks.celery_app import update_top_100_ranking
            result = update_top_100_ranking()
            logger.info(f"[PIPELINE] Ranking done: {result}")
        except Exception as e:
            logger.error(f"[PIPELINE] Ranking failed: {e}")

        # Step 4: Update category article counts
        logger.info("[PIPELINE] Step 4/6: Updating categories...")
        try:
            from app.tasks.celery_app import update_category_counts
            result = update_category_counts()
            logger.info(f"[PIPELINE] Categories done: {result}")
        except Exception as e:
            logger.error(f"[PIPELINE] Categories failed: {e}")

        # Step 5: Sync to AWS database
        if settings.SCHEDULE_AWS_SYNC_ENABLED:
            logger.info("[PIPELINE] Step 5/6: Syncing to AWS...")
            try:
                from app.tasks.celery_app import sync_to_aws
                result = sync_to_aws()
                logger.info(f"[PIPELINE] AWS sync done: {result}")
            except Exception as e:
                logger.error(f"[PIPELINE] AWS sync failed: {e}")
        else:
            logger.info("[PIPELINE] Step 5/6: AWS sync disabled, skipping")

        # Step 6: Social posting
        if settings.SCHEDULE_SOCIAL_ENABLED:
            logger.info("[PIPELINE] Step 6/6: Social posting...")
            try:
                from app.tasks.celery_app import post_to_social
                result = post_to_social()
                logger.info(f"[PIPELINE] Social done: {result}")
            except Exception as e:
                logger.error(f"[PIPELINE] Social failed: {e}")
        else:
            logger.info("[PIPELINE] Step 6/6: Social disabled, skipping")

        elapsed = round(time.time() - t0, 1)
        logger.info("=" * 60)
        logger.info(f"[PIPELINE] Complete in {elapsed}s")
        logger.info("=" * 60)

    finally:
        _pipeline_lock.release()


def _run_cleanup():
    """Separate cleanup job — runs less frequently."""
    try:
        from app.tasks.celery_app import cleanup_old_articles
        cleanup_old_articles()
    except Exception as e:
        logger.error(f"[CLEANUP] Failed: {e}")


def start_scheduler():
    """Start the in-process scheduler. Independent jobs for each pipeline step."""
    global _scheduler

    if not settings.SCHEDULER_ENABLED:
        logger.info("[SCHED] Scheduler disabled via SCHEDULER_ENABLED=false")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")

    # 1. Scraping — every 30 min
    if settings.SCHEDULE_SCRAPE_ENABLED:
        _scheduler.add_job(
            lambda: _run_step("scrape", "app.tasks.celery_app.scrape_all_sources"),
            IntervalTrigger(minutes=30),
            id="scrape_job", name="News Scraping",
        )
        logger.info("[SCHED] ✓ Scraping: every 30 min")

    # 2. AI Processing — every 15 min (more frequent to handle backlogs)
    if settings.SCHEDULE_AI_ENABLED:
        _scheduler.add_job(
            lambda: _run_step("ai", "app.tasks.celery_app.process_ai_batch"),
            IntervalTrigger(minutes=15),
            id="ai_job", name="AI Processing",
        )
        logger.info("[SCHED] ✓ AI Process: every 15 min")

    # 3. Ranking — every 30 min
    if settings.SCHEDULE_RANKING_ENABLED:
        _scheduler.add_job(
            lambda: _run_step("ranking", "app.tasks.celery_app.update_top_100_ranking"),
            IntervalTrigger(minutes=30),
            id="ranking_job", name="Ranking Update",
        )
        logger.info("[SCHED] ✓ Ranking: every 30 min")

    # 4. AWS Sync — every 30 min
    if settings.SCHEDULE_AWS_SYNC_ENABLED:
        _scheduler.add_job(
            lambda: _run_step("sync", "app.tasks.celery_app.sync_to_aws"),
            IntervalTrigger(minutes=30),
            id="sync_job", name="AWS Database Sync",
        )
        logger.info("[SCHED] ✓ AWS Sync: every 30 min")

    # 5. Cleanup — every 6 hours
    if settings.SCHEDULE_CLEANUP_ENABLED:
        _scheduler.add_job(
            lambda: _run_step("cleanup", "app.tasks.celery_app.cleanup_old_articles"),
            IntervalTrigger(hours=6),
            id="cleanup_job", name="Article Cleanup",
        )
        logger.info("[SCHED] ✓ Cleanup: every 6 hours")

    # Run everything once immediately on startup
    _scheduler.add_job(
        _run_startup_sequence,
        'date',
        id="startup_sequence", name="Startup Sequence",
        misfire_grace_time=120,
    )

    _scheduler.start()
    logger.info(f"[SCHED] Scheduler started — {len(_scheduler.get_jobs())} jobs")


def _run_step(name, task_path):
    """Wrapper to run a specific task path."""
    try:
        logger.info(f"[SCHED] Triggering {name}...")
        import importlib
        mod_name, func_name = task_path.rsplit('.', 1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        result = func()
        logger.info(f"[SCHED] {name} complete: {result}")
    except Exception as e:
        logger.error(f"[SCHED] {name} failed: {e}")


def _run_startup_sequence():
    """Runs all steps once at startup, sequentially, with a small delay between each."""
    logger.info("[SCHED] Starting initial startup sequence...")
    steps = [
        ("scrape", "app.tasks.celery_app.scrape_all_sources"),
        ("ai", "app.tasks.celery_app.process_ai_batch"),
        ("ranking", "app.tasks.celery_app.update_top_100_ranking"),
        ("sync", "app.tasks.celery_app.sync_to_aws"),
    ]
    for name, path in steps:
        _run_step(name, path)
        time.sleep(5)


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHED] Scheduler stopped")


def get_scheduler_status() -> dict:
    if not _scheduler:
        return {"running": False, "jobs": []}
    return {
        "running": _scheduler.running,
        "pipeline_interval_min": 30,
        "jobs": [
            {"id": j.id, "name": j.name, "next_run": str(j.next_run_time),
             "trigger": str(j.trigger)}
            for j in _scheduler.get_jobs()
        ],
    }
