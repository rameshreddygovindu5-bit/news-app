"""Dashboard metrics and statistics API."""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Date

from app.database import get_db
from app.models.models import NewsArticle, NewsSource, SchedulerLog, Category

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    # Total article counts by flag
    flag_counts = {}
    for flag in ["P", "N", "A", "Y", "D"]:
        result = await db.execute(
            select(func.count(NewsArticle.id)).where(NewsArticle.flag == flag)
        )
        flag_counts[flag] = result.scalar() or 0

    total = await db.execute(select(func.count(NewsArticle.id)))
    total_count = total.scalar() or 0

    duplicates = await db.execute(
        select(func.count(NewsArticle.id)).where(NewsArticle.is_duplicate == True)
    )
    dup_count = duplicates.scalar() or 0

    # Source counts
    sources_total = await db.execute(select(func.count(NewsSource.id)))
    sources_active = await db.execute(
        select(func.count(NewsSource.id)).where(
            NewsSource.is_enabled == True, NewsSource.is_paused == False
        )
    )

    # Source-wise stats
    source_stats_q = await db.execute(
        select(
            NewsSource.name,
            NewsSource.id,
            NewsSource.is_enabled,
            NewsSource.is_paused,
            NewsSource.last_scraped_at,
            func.count(NewsArticle.id).label("article_count"),
        )
        .outerjoin(NewsArticle, NewsArticle.source_id == NewsSource.id)
        .group_by(NewsSource.id)
        .order_by(func.count(NewsArticle.id).desc())
    )
    source_stats = [
        {
            "name": row[0],
            "id": row[1],
            "is_enabled": row[2],
            "is_paused": row[3],
            "last_scraped": row[4].isoformat() if row[4] else None,
            "article_count": row[5],
        }
        for row in source_stats_q.all()
    ]

    # Category stats
    cat_stats_q = await db.execute(
        select(
            NewsArticle.category,
            func.count(NewsArticle.id).label("count"),
        )
        .where(NewsArticle.flag.in_(["A", "Y"]), NewsArticle.category.isnot(None))
        .group_by(NewsArticle.category)
        .order_by(func.count(NewsArticle.id).desc())
    )
    category_stats = [
        {"category": row[0], "count": row[1]}
        for row in cat_stats_q.all()
    ]

    # Recent scheduler logs
    recent_logs_q = await db.execute(
        select(SchedulerLog)
        .order_by(SchedulerLog.started_at.desc())
        .limit(10)
    )
    recent_logs = [
        {
            "id": log.id,
            "job_type": log.job_type,
            "status": log.status,
            "articles_processed": log.articles_processed,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "duration": log.duration_seconds,
        }
        for log in recent_logs_q.scalars().all()
    ]

    # Daily trend (last 14 days)
    fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
    daily_q = await db.execute(
        select(
            cast(NewsArticle.created_at, Date).label("day"),
            func.count(NewsArticle.id).label("count"),
        )
        .where(NewsArticle.created_at >= fourteen_days_ago)
        .group_by(cast(NewsArticle.created_at, Date))
        .order_by(cast(NewsArticle.created_at, Date))
    )
    daily_trend = [
        {"date": str(row[0]), "count": row[1]}
        for row in daily_q.all()
    ]

    return {
        "total_articles": total_count,
        "pending_articles": flag_counts.get("P", 0),
        "new_articles": flag_counts.get("N", 0),
        "ai_processed": flag_counts.get("A", 0),
        "top_news": flag_counts.get("Y", 0),
        "deleted": flag_counts.get("D", 0),
        "duplicates": dup_count,
        "sources_count": sources_total.scalar() or 0,
        "active_sources": sources_active.scalar() or 0,
        "source_stats": source_stats,
        "category_stats": category_stats,
        "recent_scrapes": recent_logs,
        "daily_trend": daily_trend,
    }
