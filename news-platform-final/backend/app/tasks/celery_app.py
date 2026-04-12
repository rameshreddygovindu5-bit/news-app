import asyncio
import logging
import time
import uuid
import hashlib
import re
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select, update, func, and_, or_, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SyncSessionLocal
from app.models.models import (
    NewsSource, NewsArticle, Category, JobExecutionLog, 
    PostErrorLog, SyncMetadata, SourceErrorLog
)
from app.scrapers.base_scraper import ScraperFactory
from app.services.ai_service import ai_service
from app.services.social_service import social_service
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)
settings = get_settings()

# =============================================
# CELERY APP CONFIGURATION
# =============================================

celery_app = Celery(
    "news_aggregator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=3600,   # 1 hour soft limit
    task_time_limit=7200,        # 2 hour hard kill
)

# =============================================
# DYNAMIC BEAT SCHEDULE
# =============================================

def build_beat_schedule() -> dict:
    """Build beat schedule from config flags."""
    schedule = {}
    if not settings.SCHEDULER_ENABLED:
        logger.info("[SCHEDULER] All scheduling DISABLED")
        return schedule

    jobs = [
        ("scrape-all-sources", settings.SCHEDULE_SCRAPE_ENABLED,
         "app.tasks.celery_app.scrape_all_sources", settings.SCHEDULE_SCRAPE_MINUTES),
        ("process-ai-batch", settings.SCHEDULE_AI_ENABLED,
         "app.tasks.celery_app.process_ai_batch", settings.SCHEDULE_AI_MINUTES),
        ("update-top-100", settings.SCHEDULE_RANKING_ENABLED,
         "app.tasks.celery_app.update_top_100_ranking", settings.SCHEDULE_RANKING_MINUTES),
        ("sync-to-aws", settings.SCHEDULE_AWS_SYNC_ENABLED,
         "app.tasks.celery_app.sync_to_aws", settings.SCHEDULE_AWS_SYNC_MINUTES),
        ("update-category-counts", settings.SCHEDULE_CATEGORY_COUNT_ENABLED,
         "app.tasks.celery_app.update_category_counts", settings.SCHEDULE_CATEGORY_MINUTES),
        ("cleanup-old-articles", settings.SCHEDULE_CLEANUP_ENABLED,
         "app.tasks.celery_app.cleanup_old_articles", settings.SCHEDULE_CLEANUP_MINUTES),
        ("post-to-social", settings.SCHEDULE_SOCIAL_ENABLED,
         "app.tasks.celery_app.post_to_social", settings.SCHEDULE_SOCIAL_MINUTES),
    ]
    for key, enabled, task, minutes in jobs:
        if enabled:
            schedule[key] = {"task": task, "schedule": crontab(minute=str(minutes) if minutes else "0")}
            logger.info(f"[SCHEDULER] ON:  {key} every {minutes}m")
        else:
            logger.info(f"[SCHEDULER] OFF: {key}")
    return schedule

celery_app.conf.beat_schedule = build_beat_schedule()

def get_db():
    return SyncSessionLocal()

# =============================================
# JOB EXECUTION FRAMEWORK (Distributed Lock)
# =============================================

def log_job(db: Session, job_name: str, triggered_by: str = "cron") -> Optional[JobExecutionLog]:
    """Acquire idempotency lock via DB unique constraint on RUNNING status."""
    run_id = str(uuid.uuid4())
    
    # Check for stale locks (> 2 hours) and fail them
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    db.execute(
        update(JobExecutionLog)
        .where(JobExecutionLog.status == "RUNNING", JobExecutionLog.started_at < stale_cutoff)
        .values(status="FAILED", ended_at=func.now(), error_summary="Stale lock cleaned up")
    )
    db.commit()

    # Raw SQL for atomic lock
    sql = text("""
        INSERT INTO job_execution_log (job_name, run_id, started_at, status, triggered_by)
        SELECT :name, :id, NOW(), 'RUNNING', :trigger
        WHERE NOT EXISTS (
            SELECT 1 FROM job_execution_log WHERE job_name = :name AND status = 'RUNNING'
        )
        RETURNING id;
    """)
    result = db.execute(sql, {"name": job_name, "id": run_id, "trigger": triggered_by}).fetchone()
    
    if not result:
        logger.info(f"[JOB] {job_name} already running. Skipping.")
        return None
    
    db.commit()
    return db.query(JobExecutionLog).get(result[0])

def complete_job(db: Session, log: JobExecutionLog, rows_ok: int, rows_err: int, error_summary: str = None):
    """Finalize job and release lock."""
    if not log: return
    status = "DONE"
    if rows_err > 0: status = "PARTIAL" if rows_ok > 0 else "FAILED"
    
    log.status = status
    log.rows_ok = rows_ok
    log.rows_err = rows_err
    log.error_summary = error_summary
    log.ended_at = datetime.now(timezone.utc)
    log.duration_s = (log.ended_at - log.started_at).total_seconds()
    db.commit()
    logger.info(f"[JOB] {log.job_name} finished as {status}")

# =============================================
# SCRAPING PIPELINE
# =============================================

def normalize_title(title: str) -> str:
    if not title: return ""
    return re.sub(r'[^\w\s]', '', title.lower()).strip()

def get_content_hash(source_id: int, title: str) -> str:
    norm = normalize_title(title)
    return hashlib.sha256(f"{source_id}{norm}".encode()).hexdigest()

@celery_app.task(name="app.tasks.celery_app.scrape_all_sources")
def scrape_all_sources():
    db = get_db()
    log = log_job(db, "scrape_sources")
    if not log: return
    try:
        sources_q = db.query(NewsSource).filter(NewsSource.is_enabled == True, NewsSource.is_paused == False)
        if settings.ENABLED_SOURCES:
            enabled_list = [s.strip().lower() for s in settings.ENABLED_SOURCES.split(",")]
            sources_q = sources_q.filter(func.lower(NewsSource.name).in_(enabled_list))
        sources = sources_q.all()
        if not sources:
            complete_job(db, log, 0, 0, "No sources")
            return

        ok = err = 0
        with ThreadPoolExecutor(max_workers=32) as pool:
            futures = {pool.submit(worker_scrape_source, s.id, log.run_id): s for s in sources}
            for future in as_completed(futures):
                res = future.result()
                ok += res.get("inserted", 0)
                err += res.get("errors", 0)
        complete_job(db, log, ok, err)
    finally:
        db.close()

@celery_app.task(name="app.tasks.celery_app.scrape_source")
def scrape_source(source_id: int):
    db = get_db()
    try:
        source = db.query(NewsSource).get(source_id)
        if not source: return
        log = log_job(db, f"scrape_{source.name.lower()}", "manual")
        if not log: return
        res = worker_scrape_source(source_id, log.run_id)
        complete_job(db, log, res.get("inserted", 0), res.get("errors", 0))
    finally:
        db.close()

def worker_scrape_source(source_id: int, run_id: str) -> Dict[str, int]:
    db = SyncSessionLocal()
    stats = {"inserted": 0, "errors": 0}
    try:
        source = db.query(NewsSource).get(source_id)
        scraper = ScraperFactory.create({"name": source.name, "url": source.url, "scraper_type": source.scraper_type, "language": source.language})
        loop = asyncio.new_event_loop()
        try:
            articles = loop.run_until_complete(scraper.scrape())
        finally:
            loop.close()

        for a in articles:
            c_hash = get_content_hash(source_id, a.title)
            if db.query(NewsArticle.id).filter(NewsArticle.content_hash == c_hash).first(): continue
            
            is_dup = False; dup_id = None
            try:
                sql = text("SELECT id FROM news_articles WHERE created_at > NOW() - interval '48 hours' AND is_duplicate=FALSE AND similarity(original_title, :t) > 0.85 LIMIT 1")
                match = db.execute(sql, {"t": a.title}).fetchone()
                if match: is_dup = True; dup_id = match[0]
            except: pass

            slug = f"{re.sub(r'[^\w\s-]', '', a.title.lower()).strip().replace(' ', '-')[:100]}-{hashlib.md5(a.url.encode()).hexdigest()[:6]}"
            new_art = NewsArticle(
                source_id=source_id, original_title=a.title, original_content=a.content or a.title,
                original_url=a.url, original_language=source.language or "en", published_at=a.published_at or datetime.now(timezone.utc),
                image_url=a.image_url, content_hash=c_hash, is_duplicate=is_dup, duplicate_of_id=dup_id,
                flag="A", ai_status="pending", rephrased_title=a.title, rephrased_content=a.content or a.title,
                category="Home", slug=slug
            )
            db.add(new_art)
            db.commit()
            stats["inserted"] += 1
        source.last_scraped_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        logger.error(f"Scrape error {source_id}: {e}")
        stats["errors"] = 1
    finally:
        db.close()
    return stats

# =============================================
# AI ENRICHMENT
# =============================================

@celery_app.task(name="app.tasks.celery_app.process_ai_batch")
def process_ai_batch():
    db = get_db()
    log = log_job(db, "ai_enrichment")
    if not log: return
    try:
        subq = db.query(NewsArticle.id).filter(NewsArticle.ai_status.in_(["pending", "unknown"]), NewsArticle.is_duplicate==False).order_by(func.random()).limit(settings.AI_BATCH_SIZE).subquery()
        db.execute(update(NewsArticle).where(NewsArticle.id.in_(select(subq))).values(ai_status="processing"))
        db.commit()
        articles = db.query(NewsArticle).filter(NewsArticle.ai_status == "processing").all()
        if not articles:
            complete_job(db, log, 0, 0, "No work")
            return
        ok = err = 0
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(worker_process_ai, a.id) for a in articles]
            for f in as_completed(futures):
                if f.result(): ok += 1
                else: err += 1
        complete_job(db, log, ok, err)
    finally:
        db.close()

def worker_process_ai(aid: int) -> bool:
    db = SyncSessionLocal()
    try:
        art = db.query(NewsArticle).get(aid)
        res = ai_service.process_article(art.original_title, art.original_content)
        art.rephrased_title = res["rephrased_title"]
        art.rephrased_content = res["rephrased_content"]
        art.category = res["category"]; art.slug = res["slug"]; art.tags = res["tags"]; art.ai_status = "completed"
        art.flag = "A"  # Mark as AI-processed
        art.processed_at = datetime.now(timezone.utc)
        meta = dict(art.scrape_metadata or {}); meta["ai_method"] = res.get("method", "unknown"); art.scrape_metadata = meta
        db.commit()
        return True
    except:
        db.rollback()
        db.execute(update(NewsArticle).where(NewsArticle.id == aid).values(ai_status="failed", ai_error_count=NewsArticle.ai_error_count + 1))
        db.commit()
        return False
    finally:
        db.close()

# =============================================
# RANKING & TOP 100
# =============================================

@celery_app.task(name="app.tasks.celery_app.update_top_100_ranking")
def update_top_100_ranking():
    db = get_db()
    log = log_job(db, "ranking")
    if not log: return
    try:
        # Reset all current top news flags
        db.execute(update(NewsArticle).where(NewsArticle.flag == "Y").values(flag="A"))
        db.commit()

        # Dynamic cutoff to ensure enough candidates
        candidate_articles = []
        for days in [2, 7, 30, 60]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            candidate_articles = db.query(NewsArticle).join(NewsSource).filter(
                NewsArticle.ai_status == "completed",
                NewsArticle.created_at >= cutoff,
                NewsArticle.is_duplicate == False,
                NewsArticle.flag.in_(["A", "Y"]),
            ).all()
            if len(candidate_articles) >= 150:
                break
        
        if not candidate_articles:
            # Absolute fallback: just take latest 200 completed articles
            candidate_articles = db.query(NewsArticle).join(NewsSource).filter(
                NewsArticle.ai_status == "completed",
                NewsArticle.is_duplicate == False,
                NewsArticle.flag.in_(["A", "Y"]),
            ).order_by(desc(NewsArticle.created_at)).limit(200).all()

        if not candidate_articles:
            complete_job(db, log, 0, 0, "No candidates")
            return

        # Calculate rank scores
        now = datetime.now(timezone.utc)
        for a in candidate_articles:
            age_hours = (now - a.created_at).total_seconds() / 3600
            # Score = (Priority weight) + (Credibility weight) + (Recency decay)
            a.rank_score = (a.source.priority * 15) + (a.source.credibility_score * 25) + (100 - (0.4 * age_hours))
        db.commit()

        # Variety-aware selection: top 15 from each category, then top 100 overall
        categories = [r[0] for r in db.execute(select(Category.name)).all()]
        if not categories:
            # Fallback if categories table is empty
            categories = list(set(a.category for a in candidate_articles if a.category))

        final_ids = []
        for cname in categories:
            cat_tops = sorted(
                [a for a in candidate_articles if a.category == cname], 
                key=lambda x: x.rank_score or 0, 
                reverse=True
            )[:20] # Take up to 20 per category
            final_ids.extend([a.id for a in cat_tops])
        
        # Unique and take top 100
        unique_ids = list(set(final_ids))
        top_100_ids = sorted(
            unique_ids, 
            key=lambda aid: next(a.rank_score for a in candidate_articles if a.id == aid), 
            reverse=True
        )[:100]

        if top_100_ids:
            db.execute(update(NewsArticle).where(NewsArticle.id.in_(top_100_ids)).values(flag="Y"))
            db.commit()
            
        complete_job(db, log, len(top_100_ids), 0)
    except Exception as e:
        db.rollback()
        logger.error(f"Ranking Task Failed: {e}")
        complete_job(db, log, 0, 0, str(e))
    finally:
        db.close()

# =============================================
# AWS SYNC
# =============================================

@celery_app.task(name="app.tasks.celery_app.sync_to_aws")
def sync_to_aws():
    db = get_db()
    log = log_job(db, "aws_sync")
    if not log: return
    try:
        # Connect to AWS
        conn = psycopg2.connect(
            host=settings.AWS_DB_HOST,
            port=settings.AWS_DB_PORT,
            dbname=settings.AWS_DB_NAME,
            user=settings.AWS_DB_USER,
            password=settings.AWS_DB_PASSWORD,
            connect_timeout=10
        )
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Sync Categories (Safe Upsert)
        try:
            cats = db.query(Category).all()
            for c in cats:
                cur.execute("""
                    INSERT INTO categories (name, slug, description, article_count) 
                    VALUES (%s, %s, %s, %s) 
                    ON CONFLICT (name) DO UPDATE SET 
                    description=EXCLUDED.description, article_count=EXCLUDED.article_count
                """, (c.name, c.slug, c.description, c.article_count))
        except Exception as e:
            logger.warning(f"Category sync failed: {e}")
        
        # 2. Sync News Sources (Safe Upsert)
        try:
            sources = db.query(NewsSource).all()
            for s in sources:
                cur.execute("""
                    INSERT INTO news_sources (id, name, url, scraper_type, language, is_enabled, credibility_score, priority) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
                    ON CONFLICT (id) DO UPDATE SET 
                    name=EXCLUDED.name, url=EXCLUDED.url, is_enabled=EXCLUDED.is_enabled, 
                    credibility_score=EXCLUDED.credibility_score, priority=EXCLUDED.priority
                """, (s.id, s.name, s.url, s.scraper_type, s.language, s.is_enabled, s.credibility_score, s.priority))
        except Exception as e:
            logger.warning(f"Source sync failed: {e}")
        
        # 3. Sync News Articles (Delta)
        meta = db.query(SyncMetadata).filter(SyncMetadata.target == "AWS_PROD").first()
        if not meta:
            meta = SyncMetadata(target="AWS_PROD", last_sync_at=datetime.now(timezone.utc) - timedelta(days=7))
            db.add(meta); db.commit()
        
        records = db.query(NewsArticle).filter(NewsArticle.updated_at > meta.last_sync_at).all()
        if not records:
            cur.close(); conn.close()
            complete_job(db, log, 0, 0, "No delta")
            return

        ok = err = 0; sync_at = datetime.now(timezone.utc)
        for art in records:
            try:
                # Use a more explicit UPSERT for articles
                sql = """
                    INSERT INTO news_articles (
                        source_id, original_title, original_content, original_url, original_language, 
                        published_at, rephrased_title, rephrased_content, category, slug, tags, 
                        flag, image_url, author, content_hash, is_duplicate, duplicate_of_id, 
                        rank_score, created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) 
                    ON CONFLICT (original_url) DO UPDATE SET 
                        rephrased_title=EXCLUDED.rephrased_title, 
                        rephrased_content=EXCLUDED.rephrased_content, 
                        category=EXCLUDED.category, 
                        slug=EXCLUDED.slug, 
                        tags=EXCLUDED.tags, 
                        flag=EXCLUDED.flag, 
                        image_url=EXCLUDED.image_url, 
                        rank_score=EXCLUDED.rank_score,
                        updated_at=EXCLUDED.updated_at
                """
                cur.execute(sql, (
                    art.source_id, art.original_title, art.original_content, art.original_url, 
                    art.original_language, art.published_at, art.rephrased_title, art.rephrased_content, 
                    art.category, art.slug, art.tags, art.flag, art.image_url, art.author, 
                    art.content_hash, art.is_duplicate, art.duplicate_of_id, 
                    art.rank_score, art.created_at, art.updated_at
                ))
                ok += 1
            except Exception as e:
                logger.error(f"Article sync error {art.id}: {e}")
                err += 1

        cur.close(); conn.close()
        meta.last_sync_at = sync_at; meta.last_rows_ok = ok; meta.last_rows_err = err; db.commit()
        complete_job(db, log, ok, err)
    except Exception as e:
        logger.error(f"AWS Sync Task Failed: {e}")
        complete_job(db, log, 0, 0, str(e))
    finally:
        db.close()

# =============================================
# MAINTENANCE & CATEGORIES
# =============================================

@celery_app.task(name="app.tasks.celery_app.update_category_counts")
def update_category_counts():
    db = get_db()
    try:
        db.execute(text("UPDATE categories c SET article_count = (SELECT COUNT(*) FROM news_articles a WHERE a.category = c.name AND a.flag != 'D')"))
        db.commit()
    finally:
        db.close()

@celery_app.task(name="app.tasks.celery_app.cleanup_old_articles")
def cleanup_old_articles():
    db = get_db()
    try:
        log = log_job(db, "maintenance")
        if not log: return
        res = db.execute(update(NewsArticle).where(NewsArticle.created_at < datetime.now(timezone.utc) - timedelta(days=15), NewsArticle.flag != "D").values(flag="D", deleted_at=func.now()))
        db.commit()
        complete_job(db, log, res.rowcount, 0)
    finally:
        db.close()

@celery_app.task(name="app.tasks.celery_app.post_to_social")
def post_to_social():
    """Post Y-flag articles to social media."""
    db = get_db()
    log = log_job(db, "social_post")
    if not log: return
    try:
        unposted = db.query(NewsArticle).filter(
            NewsArticle.flag == "Y",
            NewsArticle.is_posted_fb == False,
        ).order_by(NewsArticle.rank_score.desc()).limit(10).all()
        posted = 0
        for art in unposted:
            try:
                url = f"{settings.SOCIAL_SITE_URL}/news/{art.slug or art.id}"
                title = art.rephrased_title or art.original_title
                social_service.post_to_all(art.id, title, art.rephrased_content or "", url)
                art.is_posted_fb = True; art.is_posted_ig = True
                art.is_posted_x = True; art.is_posted_wa = True
                posted += 1
            except Exception as e:
                logger.warning(f"[SOCIAL] Article {art.id} failed: {e}")
        db.commit()
        complete_job(db, log, posted, 0)
    except Exception as e:
        logger.error(f"[SOCIAL] Error: {e}")
        complete_job(db, log, 0, 0, str(e))
    finally:
        db.close()

@celery_app.task(name="app.tasks.celery_app.run_full_pipeline")
def run_full_pipeline(source_id: Optional[int] = None):
    """Executes the complete news cycle in sequence."""
    logger.info("================ STARTING FULL INTEGRATED PIPELINE ================")
    
    # 1. Scrape
    if source_id:
        scrape_source(source_id)
    else:
        scrape_all_sources()
    
    # 2. AI process
    process_ai_batch()
    
    # 3. Ranking
    update_top_100_ranking()
    
    # 4. Sync to AWS
    sync_to_aws()
    
    # 5. Social post
    post_to_social()
    
    logger.info("================ FULL INTEGRATED PIPELINE COMPLETED ================")

if __name__ == "__main__":
    # Integration: Allow running the full pipeline directly via 'python -m app.tasks.celery_app'
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        run_full_pipeline()
    else:
        print("Usage: python -m app.tasks.celery_app --run")
