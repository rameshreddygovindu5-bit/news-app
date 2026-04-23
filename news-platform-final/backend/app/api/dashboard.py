import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Date

from app.database import get_db
from app.models.models import NewsArticle, NewsSource, SchedulerLog, Category

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    from app.models.models import NewsArticle, NewsSource, JobExecutionLog
    import psycopg2
    from app.config import get_settings
    settings = get_settings()

    local_stats = {
        "total": 0, "processed": 0, "pending_ai": 0, "top": 0,
        "pending_approval": 0, "new": 0, "failed_ai": 0
    }
    aws_data = {"total": 0, "processed": 0, "top": 0, "status": "offline"}
    recent_logs = []
    category_stats = []
    
    debug_info = {"error": None, "trace": None}
    # --- 1. LOCAL DATA ---
    try:
        flag_res = await db.execute(select(NewsArticle.flag, func.count(NewsArticle.id)).group_by(NewsArticle.flag))
        for fl, count in flag_res.all():
            if fl == "P": local_stats["pending_approval"] = count
            elif fl == "N": local_stats["new"] = count
            elif fl == "A": local_stats["processed"] += count
            elif fl == "Y": local_stats["top"] = count; local_stats["processed"] += count
        
        local_stats["total"] = sum(v for k,v in local_stats.items() if k not in ["failed_ai", "processed"]) + local_stats.get("processed",0)
        # Actually total is just sum of A, Y, P, N.
        # Total = all articles in DB
        total_res = await db.execute(select(func.count(NewsArticle.id)).where(NewsArticle.flag != "D"))
        local_stats["total"] = (await db.execute(select(func.count(NewsArticle.id)))).scalar() or 0

        # Count AI processed using ALL known success status codes
        AI_PROCESSED_STATUSES = [
            "completed", "AI_SUCCESS", "AI_RETRY_SUCCESS",
            "UNPROCESSED_AI_FALLBACK", "GOOGLE_NEWS_NO_AI",
            "GOOGLE_NEWS_LOCAL", "LOCAL_PARAPHRASE", "REWRITE_FAILED",
        ]
        ai_res = await db.execute(select(NewsArticle.ai_status, func.count(NewsArticle.id)).group_by(NewsArticle.ai_status))
        ai_processed_count = 0
        ai_pending_count = 0
        ai_failed_count = 0
        for st, count in ai_res.all():
            if st in ("pending", "processing", "unknown") or st is None:
                ai_pending_count += count
            elif st in AI_PROCESSED_STATUSES:
                ai_processed_count += count
            elif st == "failed":
                ai_failed_count += count
        local_stats["pending_ai"] = ai_pending_count
        local_stats["processed"] = ai_processed_count
        local_stats["failed_ai"] = ai_failed_count

        logs_res = await db.execute(select(JobExecutionLog).order_by(JobExecutionLog.started_at.desc()).limit(10))
        recent_logs = [{"id": l.id, "job_name": l.job_name, "status": l.status, "rows_ok": l.rows_ok, "rows_err": l.rows_err} for l in logs_res.scalars().all()]

        cat_res = await db.execute(select(NewsArticle.category, func.count(NewsArticle.id)).where(NewsArticle.flag != "D").group_by(NewsArticle.category))
        category_stats = [{"category": r[0] or "Uncategorized", "count": r[1]} for r in cat_res.all()]
    except Exception as e:
        import traceback
        debug_info["error"] = str(e)
        debug_info["trace"] = traceback.format_exc()
        logger.error(f"Local Stats Error: {e}")

    # --- 2. AWS DATA ---
    aws_debug = None
    try:
        with psycopg2.connect(
            host=settings.AWS_DB_HOST, port=settings.AWS_DB_PORT, dbname=settings.AWS_DB_NAME,
            user=settings.AWS_DB_USER, password=settings.AWS_DB_PASSWORD, connect_timeout=3
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM news_articles WHERE flag != 'D'")
                aws_data["total"] = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM news_articles WHERE flag IN ('A', 'Y')")
                aws_data["processed"] = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM news_articles WHERE flag = 'Y'")
                aws_data["top"] = cur.fetchone()[0]
                aws_data["status"] = "online"
    except Exception as e:
        aws_debug = str(e)
        logger.warning(f"AWS Stats unreachable: {e}")

    final_res = {
        "local": local_stats,
        "aws": aws_data,
        "recent_scrapes": recent_logs,
        "category_stats": category_stats,
        "sources_count": (await db.execute(select(func.count(NewsSource.id)))).scalar() or 0,
        "active_sources": (await db.execute(select(func.count(NewsSource.id)).where(NewsSource.is_enabled==True))).scalar() or 0,
        "debug": debug_info,
        "aws_error": aws_debug
    }
    return final_res
