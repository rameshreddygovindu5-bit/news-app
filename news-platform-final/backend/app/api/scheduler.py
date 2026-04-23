"""Scheduler management, configuration, and manual trigger API."""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.config import get_settings
from app.models.models import SchedulerLog, AdminUser, NewsArticle, SourceErrorLog, PostErrorLog
from app.schemas.schemas import (
    SchedulerLogResponse, SchedulerAction,
    SchedulerConfigResponse, SchedulerConfigUpdate
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])
settings = get_settings()


@router.get("/logs", response_model=List[SchedulerLogResponse])
async def get_scheduler_logs(
    job_name: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(SchedulerLog).order_by(desc(SchedulerLog.started_at)).limit(limit)
    if job_name:
        query = query.where(SchedulerLog.job_name == job_name)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/config", response_model=SchedulerConfigResponse)
async def get_scheduler_config(
    current_user: AdminUser = Depends(get_current_user),
):
    """Get current scheduler configuration and flags."""
    return SchedulerConfigResponse(
        scheduler_enabled=settings.SCHEDULER_ENABLED,
        scrape_enabled=settings.SCHEDULE_SCRAPE_ENABLED,
        ai_enabled=settings.SCHEDULE_AI_ENABLED,
        ranking_enabled=settings.SCHEDULE_RANKING_ENABLED,
        social_enabled=settings.SCHEDULE_SOCIAL_ENABLED,
        aws_sync_enabled=settings.SCHEDULE_AWS_SYNC_ENABLED,
        category_count_enabled=settings.SCHEDULE_CATEGORY_COUNT_ENABLED,
        cleanup_enabled=settings.SCHEDULE_CLEANUP_ENABLED,
        scrape_minutes=settings.SCHEDULE_SCRAPE_MINUTES,
        ai_minutes=settings.SCHEDULE_AI_MINUTES,
        ranking_minutes=settings.SCHEDULE_RANKING_MINUTES,
        social_minutes=settings.SCHEDULE_SOCIAL_MINUTES,
        aws_sync_minutes=settings.SCHEDULE_AWS_SYNC_MINUTES,
        category_minutes=settings.SCHEDULE_CATEGORY_MINUTES,
        cleanup_minutes=settings.SCHEDULE_CLEANUP_MINUTES,
        ai_provider_chain=settings.AI_PROVIDER_CHAIN,
        ai_batch_size=settings.AI_BATCH_SIZE,
        ai_concurrency=settings.AI_CONCURRENCY,
        top_news_count=settings.TOP_NEWS_COUNT,
        top_news_max_age_days=settings.TOP_NEWS_MAX_AGE_DAYS,
        top_news_min_per_category=settings.TOP_NEWS_MIN_PER_CATEGORY,
        top_news_max_per_category=settings.TOP_NEWS_MAX_PER_CATEGORY,
    )


@router.put("/config")
async def update_scheduler_config(
    data: SchedulerConfigUpdate,
    current_user: AdminUser = Depends(get_current_user),
):
    """Toggle scheduler flags and update intervals at runtime.
    Note: Changes are in-memory and reset on restart. For permanent changes, update .env.
    """
    updated = {}
    flag_fields = {
        "scrape_enabled": "SCHEDULE_SCRAPE_ENABLED",
        "ai_enabled": "SCHEDULE_AI_ENABLED",
        "ranking_enabled": "SCHEDULE_RANKING_ENABLED",
        "social_enabled": "SCHEDULE_SOCIAL_ENABLED",
        "aws_sync_enabled": "SCHEDULE_AWS_SYNC_ENABLED",
        "category_count_enabled": "SCHEDULE_CATEGORY_COUNT_ENABLED",
        "cleanup_enabled": "SCHEDULE_CLEANUP_ENABLED",
    }
    minute_fields = {
        "scrape_minutes": "SCHEDULE_SCRAPE_MINUTES",
        "ai_minutes": "SCHEDULE_AI_MINUTES",
        "ranking_minutes": "SCHEDULE_RANKING_MINUTES",
        "social_minutes": "SCHEDULE_SOCIAL_MINUTES",
        "aws_sync_minutes": "SCHEDULE_AWS_SYNC_MINUTES",
        "category_minutes": "SCHEDULE_CATEGORY_MINUTES",
        "cleanup_minutes": "SCHEDULE_CLEANUP_MINUTES",
    }

    for field, setting_attr in flag_fields.items():
        val = getattr(data, field, None)
        if val is not None:
            setattr(settings, setting_attr, val)
            updated[field] = val

    for field, setting_attr in minute_fields.items():
        val = getattr(data, field, None)
        if val is not None:
            setattr(settings, setting_attr, val)
            updated[field] = val

    return {"message": "Scheduler config updated", "updated": updated}


@router.get("/status")
async def get_scheduler_running_status(
    current_user: AdminUser = Depends(get_current_user),
):
    """Get in-process scheduler status — which jobs are running and when they next fire."""
    from app.tasks.scheduler import get_scheduler_status
    return get_scheduler_status()


@router.get("/social-status")
async def get_social_status(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Get social posting status — how many articles posted to each platform."""
    from app.models.models import NewsArticle
    from sqlalchemy import func

    total_y = (await db.execute(
        select(func.count(NewsArticle.id)).where(NewsArticle.flag == "Y")
    )).scalar() or 0

    posted_fb = (await db.execute(
        select(func.count(NewsArticle.id)).where(NewsArticle.flag == "Y", NewsArticle.is_posted_fb == True)
    )).scalar() or 0

    posted_ig = (await db.execute(
        select(func.count(NewsArticle.id)).where(NewsArticle.flag == "Y", NewsArticle.is_posted_ig == True)
    )).scalar() or 0

    posted_x = (await db.execute(
        select(func.count(NewsArticle.id)).where(NewsArticle.flag == "Y", NewsArticle.is_posted_x == True)
    )).scalar() or 0

    posted_wa = (await db.execute(
        select(func.count(NewsArticle.id)).where(NewsArticle.flag == "Y", NewsArticle.is_posted_wa == True)
    )).scalar() or 0

    return {
        "total_top_news": total_y,
        "posted_facebook": posted_fb,
        "posted_instagram": posted_ig,
        "posted_x": posted_x,
        "posted_whatsapp": posted_wa,
        "unposted": total_y - posted_fb,
    }


@router.post("/trigger")
async def trigger_action(
    action: SchedulerAction,
    current_user: AdminUser = Depends(get_current_user),
):
    """Trigger a pipeline step. Tries Celery async first, falls back to sync execution."""
    from app.tasks.celery_app import (
        scrape_source, scrape_all_sources, process_ai_batch,
        update_top_100_ranking, sync_to_aws, full_integrity_sync, run_full_pipeline,
        cleanup_old_articles, update_category_counts, post_to_social,
    )

    task_map = {
        "trigger_scrape": (
            lambda: scrape_source.delay(action.source_id) if action.source_id else scrape_all_sources.delay(),
            lambda: scrape_source(action.source_id) if action.source_id else scrape_all_sources(),
            "Scrape"
        ),
        "trigger_ai": (lambda: process_ai_batch.delay(), lambda: process_ai_batch(), "AI processing"),
        "trigger_ranking": (lambda: update_top_100_ranking.delay(), lambda: update_top_100_ranking(), "Ranking"),
        "trigger_social": (lambda: post_to_social.delay(), lambda: post_to_social(), "Social posting"),
        "trigger_sync": (lambda: sync_to_aws.delay(), lambda: sync_to_aws(), "AWS sync"),
        "trigger_deep_sync": (lambda: full_integrity_sync.delay(), lambda: full_integrity_sync(), "Deep integrity sync"),
        "trigger_cleanup": (lambda: cleanup_old_articles.delay(), lambda: cleanup_old_articles(), "Cleanup"),
        "trigger_categories": (lambda: update_category_counts.delay(), lambda: update_category_counts(), "Category update"),
        "trigger_pipeline": (
            lambda: run_full_pipeline.delay(action.source_id),
            lambda: run_full_pipeline(action.source_id),
            "Full pipeline"
        ),
    }

    entry = task_map.get(action.action)
    if not entry:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown action: {action.action}")

    async_fn, sync_fn, label = entry

    # Try Celery (async via Redis) first, fall back to direct sync execution
    try:
        async_fn()
        return {"message": f"{label} triggered (async)", "action": action.action, "mode": "celery"}
    except Exception as celery_err:
        import logging
        logging.getLogger(__name__).warning(f"Celery unavailable ({celery_err}), running {label} synchronously")
        try:
            import asyncio
            result = await asyncio.to_thread(sync_fn)
            return {"message": f"{label} completed (sync)", "action": action.action, "mode": "sync", "result": str(result)[:500]}
        except Exception as sync_err:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=f"{label} failed: {str(sync_err)[:200]}")


@router.get("/source-errors")
async def get_source_errors(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get recent scraper errors."""
    query = select(SourceErrorLog).order_by(desc(SourceErrorLog.created_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/post-errors")
async def get_post_errors(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get recent social media posting errors."""
    query = select(PostErrorLog).order_by(desc(PostErrorLog.created_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/set-image-mode")
async def set_image_mode(
    use_custom: bool,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Toggle image display mode:
    - use_custom=true  → show category placeholder images (default, safe)
    - use_custom=false → show scraped article images when available
    
    Also triggers a background job to update image_url for all articles.
    """
    from app.config import get_settings
    settings = get_settings()
    # Hot-patch the setting (persists for session; restart to reset from .env)
    settings.USE_CUSTOM_IMAGES = use_custom

    # Trigger background image update
    import threading
    def _update_images():
        from app.database import SyncSessionLocal
        from app.models.models import NewsArticle
        from sqlalchemy import update
        _db = SyncSessionLocal()
        try:
            _CAT_IMG = {
                "Business": "/placeholders/business.png",
                "Tech": "/placeholders/tech.png", "Technology": "/placeholders/tech.png",
                "Entertainment": "/placeholders/entertainment.png",
                "Sports": "/placeholders/sports.png", "Health": "/placeholders/health.png",
                "Science": "/placeholders/science.png", "Politics": "/placeholders/politics.png",
                "World": "/placeholders/world.png", "International": "/placeholders/world.png",
                "India": "/placeholders/general.png", "U.S.": "/placeholders/world.png",
                "Andhra Pradesh": "/placeholders/politics.png",
                "Telangana": "/placeholders/politics.png",
            }
            if use_custom:
                # Set all articles to category placeholder
                for cat, img in _CAT_IMG.items():
                    _db.execute(
                        update(NewsArticle)
                        .where(NewsArticle.category == cat)
                        .values(image_url=img)
                    )
                # Default for unmapped categories
                _db.execute(
                    update(NewsArticle)
                    .where(NewsArticle.category.notin_(list(_CAT_IMG.keys())))
                    .values(image_url="/placeholders/general.png")
                )
            # For use_custom=false, keep existing scraped URLs intact
            _db.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[IMAGE-MODE] Update failed: {e}")
        finally:
            _db.close()
    
    threading.Thread(target=_update_images, daemon=True).start()
    mode = "custom placeholders" if use_custom else "scraped article images"
    return {"message": f"Image mode set to {mode}. Updating all articles in background."}
