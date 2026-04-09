"""
Celery task definitions for:
- News scraping
- AI processing
- Top 100 ranking
- Cleanup
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SyncSessionLocal
from app.models.models import NewsSource, NewsArticle, SchedulerLog, Category
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
    # â”€â”€â”€ FIX: was 300/600 â†’ task died mid-scrape â”€â”€â”€
    task_soft_time_limit=3600,   # 1 hour soft limit
    task_time_limit=7200,        # 2 hour hard kill
)

# =============================================
# DYNAMIC BEAT SCHEDULE (flag-based from config)
# =============================================

def build_beat_schedule() -> dict:
    """Build beat schedule from config flags. Disabled jobs are excluded."""
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
            schedule[key] = {"task": task, "schedule": crontab(minute=minutes)}
            logger.info(f"[SCHEDULER] ON:  {key} at minute={minutes}")
        else:
            logger.info(f"[SCHEDULER] OFF: {key}")
    return schedule


celery_app.conf.beat_schedule = build_beat_schedule()


def get_db():
    return SyncSessionLocal()


def log_job(db: Session, job_type: str, source_id=None) -> SchedulerLog:
    log = SchedulerLog(
        job_type=job_type,
        source_id=source_id,
        status="started",
        started_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def complete_job(db: Session, log: SchedulerLog, status: str, count: int = 0, error: str = None):
    log.status = status
    log.articles_processed = count
    log.error_message = error
    log.completed_at = datetime.now(timezone.utc)
    log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
    db.commit()


# =============================================
# SCRAPING TASKS
# =============================================

@celery_app.task(name="app.tasks.celery_app.scrape_source")
def scrape_source(source_id: int):
    """Scrape a single news source."""
    db = get_db()
    try:
        source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
        if not source or not source.is_enabled or source.is_paused:
            logger.info(f"Source {source_id} is disabled or paused, skipping")
            return {"status": "skipped", "source_id": source_id}

        log = log_job(db, "scrape", source_id)

        # Build source config dict
        source_config = {
            "name": source.name,
            "url": source.url,
            "language": source.language,
            "scraper_type": source.scraper_type,
            "scraper_config": source.scraper_config or {},
        }

        # Create scraper and run it
        scraper = ScraperFactory.create(source_config)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            articles = loop.run_until_complete(scraper.scrape())
        finally:
            loop.close()

        # Store articles
        inserted_count = 0
        skipped_duplicate = 0
        skipped_invalid = 0

        for article in articles:
            if not article.is_valid():
                skipped_invalid += 1
                continue

            # â”€â”€â”€ FIX: Simple duplicate check â€” URL or hash only â”€â”€â”€
            # The old fuzzy SequenceMatcher check loaded ALL articles
            # from last 24h and ran O(nÂ²) comparisons, which:
            #   a) Ate the entire Celery time limit
            #   b) Falsely rejected articles with similar titles
            existing = None
            if article.url:
                existing = db.query(NewsArticle.id).filter(
                    or_(
                        NewsArticle.content_hash == article.content_hash,
                        NewsArticle.original_url == article.url,
                    )
                ).first()
            else:
                existing = db.query(NewsArticle.id).filter(
                    NewsArticle.content_hash == article.content_hash
                ).first()

            if existing:
                skipped_duplicate += 1
                continue

            new_article = NewsArticle(
                source_id=source.id,
                original_title=article.title,
                original_content=article.content,
                original_url=article.url,
                original_language=source.language,
                published_at=article.published_at or datetime.now(timezone.utc),
                content_hash=article.content_hash,
                image_url=article.image_url,
                author=article.author,
                scrape_metadata=article.metadata,
                flag="N",
                is_duplicate=False,
            )
            db.add(new_article)
            inserted_count += 1

            logger.info(
                f"[NEW] {source.name} | {new_article.original_title[:80]} | {new_article.original_url}"
            )

        # Update source last scraped time
        source.last_scraped_at = datetime.now(timezone.utc)
        db.commit()

        complete_job(db, log, "completed", inserted_count)
        logger.info(
            f"[{source.name}] Scrape done: "
            f"{inserted_count} new, {skipped_duplicate} duplicates, "
            f"{skipped_invalid} invalid, {len(articles)} total scraped"
        )

        return {
            "status": "success",
            "source": source.name,
            "articles_scraped": len(articles),
            "articles_inserted": inserted_count,
            "duplicates_skipped": skipped_duplicate,
        }

    except Exception as e:
        logger.error(f"Error scraping source {source_id}: {e}", exc_info=True)
        db.rollback()
        return {"status": "error", "source_id": source_id, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.celery_app.scrape_all_sources")
def scrape_all_sources():
    """Trigger scraping for all enabled, non-paused sources."""
    db = get_db()
    try:
        # Filter by enabled sources in settings if specified
        query = db.query(NewsSource).filter(
            NewsSource.is_enabled == True,
            NewsSource.is_paused == False,
        )
        
        if settings.ENABLED_SOURCES:
            enabled_list = [s.strip().lower() for s in settings.ENABLED_SOURCES.split(",")]
            # Filter where source name (lower) is in the list
            query = query.filter(func.lower(NewsSource.name).in_(enabled_list))
            
        sources = query.all()

        results = []
        for source in sources:
            if source.last_scraped_at:
                elapsed = (datetime.now(timezone.utc) - source.last_scraped_at.replace(tzinfo=timezone.utc)).total_seconds()
                if elapsed < source.scrape_interval_minutes * 60:
                    continue

            scrape_source.delay(source.id)
            results.append({"source": source.name, "dispatched": True})

        logger.info(f"Dispatched scraping for {len(results)} sources")
        return {"dispatched": len(results), "sources": results}

    finally:
        db.close()


# =============================================
# AI PROCESSING TASKS
# =============================================

@celery_app.task(name="app.tasks.celery_app.process_ai_single")
def process_ai_single(article_id: int):
    """AI process a single article."""
    db = get_db()
    try:
        article = db.query(NewsArticle).filter(
            NewsArticle.id == article_id,
            NewsArticle.flag == "N",
            NewsArticle.is_duplicate == False,
        ).first()

        if not article:
            return {"status": "skipped", "article_id": article_id}

        result = ai_service.process_article(
            title=article.original_title,
            content=article.original_content or "",
        )

        article.original_language = result["original_language"]
        article.translated_title = result["translated_title"]
        article.translated_content = result["translated_content"]
        article.rephrased_title = result["rephrased_title"]
        article.rephrased_content = result["rephrased_content"]
        article.slug = result.get("slug")
        article.category = result["category"]
        article.tags = result["tags"]
        article.flag = "A"
        article.processed_at = datetime.now(timezone.utc)


        db.commit()
        logger.info(f"AI processed article {article_id}: {result['category']}")

        return {"status": "success", "article_id": article_id, "category": result["category"]}

    except Exception as e:
        logger.error(f"AI processing failed for article {article_id}: {e}")
        # Increment error count so batch skips after 3 failures
        try:
            article = db.query(NewsArticle).filter(NewsArticle.id == article_id).first()
            if article:
                article.ai_error_count = (article.ai_error_count or 0) + 1
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
        return {"status": "error", "article_id": article_id, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.celery_app.process_ai_batch")
def process_ai_batch():
    """Process a batch of unprocessed articles in parallel."""
    db = get_db()
    try:
        log = log_job(db, "ai_process")

        # FIX: Use config values, skip articles that failed 3+ times
        articles = db.query(NewsArticle).filter(
            NewsArticle.flag == "N",
            NewsArticle.is_duplicate == False,
            NewsArticle.ai_error_count < 3,
        ).order_by(
            NewsArticle.published_at.desc().nullslast(),
            NewsArticle.created_at.desc()
        ).limit(settings.AI_BATCH_SIZE).all()

        if not articles:
            complete_job(db, log, "completed", 0)
            return {"status": "no_articles"}

        sem = asyncio.Semaphore(settings.AI_CONCURRENCY)

        async def process_one(article):
            try:
                async with sem:
                    result = await asyncio.to_thread(
                        ai_service.process_article,
                        title=article.original_title,
                        content=article.original_content or "",
                    )
                    
                    article.original_language = result["original_language"]
                    article.translated_title = result["translated_title"]
                    article.translated_content = result["translated_content"]
                    article.rephrased_title = result["rephrased_title"]
                    article.rephrased_content = result["rephrased_content"]
                    article.slug = result.get("slug")
                    article.category = result["category"]
                    article.tags = result["tags"]
                    article.flag = "A"
                    article.processed_at = datetime.now(timezone.utc)

                    return True
            except Exception as e:
                logger.error(f"Failed processing article {article.id}: {e}")
                article.ai_error_count = (article.ai_error_count or 0) + 1
                return False

        async def run_batch():
            tasks = [process_one(a) for a in articles]
            results = await asyncio.gather(*tasks)
            return sum(1 for r in results if r)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            processed = loop.run_until_complete(run_batch())
            db.commit()
        finally:
            loop.close()

        complete_job(db, log, "completed", processed)
        logger.info(f"AI batch processed {processed}/{len(articles)} articles in PARALLEL")

        return {"status": "success", "processed": processed, "total": len(articles)}

    except Exception as e:
        logger.error(f"AI batch processing error: {e}")
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


# =============================================
# RANKING TASKS
# =============================================

@celery_app.task(name="app.tasks.celery_app.update_top_100_ranking")
def update_top_100_ranking():
    """Update top news ranking with category diversity and age filter.
    
    Ensures:
    - Only articles from last TOP_NEWS_MAX_AGE_DAYS (default 60 days)
    - At least MIN_PER_CATEGORY from each category  
    - No more than MAX_PER_CATEGORY from any single category
    - Total capped at TOP_NEWS_COUNT
    """
    db = get_db()
    try:
        log = log_job(db, "ranking")

        # 1. Reset ALL current Y → A
        db.query(NewsArticle).filter(
            NewsArticle.flag == "Y"
        ).update({"flag": "A"}, synchronize_session=False)
        db.commit()

        # 2. Age cutoff
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.TOP_NEWS_MAX_AGE_DAYS)

        # 3. Get ALL eligible articles grouped by category
        eligible = db.query(NewsArticle).filter(
            NewsArticle.flag == "A",
            NewsArticle.is_duplicate == False,
            or_(NewsArticle.published_at >= cutoff, NewsArticle.created_at >= cutoff),
        ).order_by(
            NewsArticle.published_at.desc().nullslast(),
            NewsArticle.created_at.desc(),
        ).all()

        # 4. Category-diverse selection
        by_cat: dict = {}
        for a in eligible:
            cat = a.category or "Home"
            by_cat.setdefault(cat, []).append(a)

        selected = []
        remaining_pool = []

        # First pass: guarantee MIN per category
        for cat, articles in by_cat.items():
            min_count = min(settings.TOP_NEWS_MIN_PER_CATEGORY, len(articles))
            selected.extend(articles[:min_count])
            remaining_pool.extend(articles[min_count:settings.TOP_NEWS_MAX_PER_CATEGORY])

        # Second pass: fill to TOP_NEWS_COUNT from remaining
        remaining_pool.sort(key=lambda a: a.published_at or a.created_at, reverse=True)
        for a in remaining_pool:
            if len(selected) >= settings.TOP_NEWS_COUNT:
                break
            if a not in selected:
                selected.append(a)

        # 5. Mark as Y with rank scores
        for i, article in enumerate(selected[:settings.TOP_NEWS_COUNT]):
            article.rank_score = settings.TOP_NEWS_COUNT - i
            article.flag = "Y"
        
        db.commit()
        complete_job(db, log, "completed", len(selected))
        logger.info(f"[RANKING] Selected {len(selected)} articles across {len(by_cat)} categories (age <= {settings.TOP_NEWS_MAX_AGE_DAYS}d)")

        return {"status": "success", "top_count": len(selected), "categories": len(by_cat)}

    except Exception as e:
        logger.error(f"Ranking update error: {e}")
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


# =============================================
# SOCIAL POSTING TASK (runs after ranking)
# =============================================

@celery_app.task(name="app.tasks.celery_app.post_to_social")
def post_to_social():
    """Post newly-ranked Y articles that haven't been shared yet."""
    if not settings.SOCIAL_POST_ENABLED:
        return {"status": "disabled"}
    
    db = get_db()
    try:
        log = log_job(db, "social_post")
        
        # Find Y-flag articles not yet posted
        unposted = db.query(NewsArticle).filter(
            NewsArticle.flag == "Y",
            NewsArticle.is_posted_fb == False,
        ).order_by(NewsArticle.rank_score.desc()).limit(20).all()
        
        posted = 0
        for article in unposted:
            try:
                url = f"{settings.SOCIAL_SITE_URL}/news/{article.slug or article.id}"
                title = article.rephrased_title or article.original_title
                social_service.post_to_all(article.id, title, article.rephrased_content or "", url)
                article.is_posted_fb = True
                article.is_posted_ig = True
                article.is_posted_x = True
                article.is_posted_wa = True
                posted += 1
            except Exception as e:
                logger.warning(f"[SOCIAL] Failed for {article.id}: {e}")
        
        db.commit()
        complete_job(db, log, "completed", posted)
        logger.info(f"[SOCIAL] Posted {posted}/{len(unposted)} articles")
        return {"status": "success", "posted": posted}
    except Exception as e:
        logger.error(f"Social posting error: {e}")
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


# =============================================
# CATEGORY COUNT TASK
# =============================================

@celery_app.task(name="app.tasks.celery_app.update_category_counts")
def update_category_counts():
    """Update article counts per category."""
    db = get_db()
    try:
        categories = db.query(Category).all()
        for cat in categories:
            count = db.query(func.count(NewsArticle.id)).filter(
                NewsArticle.category == cat.name,
                NewsArticle.flag.in_(["A", "Y"]),
                NewsArticle.is_duplicate == False,
            ).scalar()
            cat.article_count = count or 0

        db.commit()
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Category count update error: {e}")
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
# =============================================
# AWS SYNC TASK
# =============================================

@celery_app.task(name="app.tasks.celery_app.sync_to_aws")
def sync_to_aws():
    """Sync local data to AWS remote database."""
    logger.info("Starting AWS Remote Database Sync...")
    
    src_conn = None
    tgt_conn = None
    
    try:
        # Register JSON adapter
        psycopg2.extras.register_default_jsonb(globally=True)
        
        # Connections
        src_conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
        tgt_conn = psycopg2.connect(settings.AWS_DATABASE_URL)
        
        tables = [
            ('admin_users', None),
            ('news_sources', None),
            ('categories', None), # mode handles later
            ('news_articles', None),
        ]
        
        processed_total = 0
        
        for table, extra in tables:
            # 1. Get Shared Columns
            def get_cols(conn, t):
                cur = conn.cursor()
                cur.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema='public' AND table_name=%s
                """, (t,))
                return [r[0] for r in cur.fetchall()]
            
            src_cols = get_cols(src_conn, table)
            tgt_cols = set(get_cols(tgt_conn, table))
            shared_cols = [c for c in src_cols if c in tgt_cols]
            
            # 2. Extract Data
            src_cur = src_conn.cursor()
            col_list = ', '.join(f'"{c}"' for c in shared_cols)
            # Only sync published articles to AWS (not pending/deleted)
            if table == 'news_articles':
                src_cur.execute(f'SELECT {col_list} FROM {table} WHERE flag IN (\'A\', \'Y\')')
            else:
                src_cur.execute(f'SELECT {col_list} FROM {table}')
            rows = src_cur.fetchall()
            
            if not rows: continue
            
            # 3. Upsert into Target
            tgt_cur = tgt_conn.cursor()
            insert_col_str = ', '.join(f'"{c}"' for c in shared_cols)
            placeholders = ', '.join(['%s'] * len(shared_cols))
            
            # Upsert logic (id as PK)
            update_cols = [c for c in shared_cols if c != 'id']
            if update_cols:
                set_clause = ', '.join([f'"{c}" = EXCLUDED."{c}"' for c in update_cols])
                conflict = f'ON CONFLICT (id) DO UPDATE SET {set_clause}'
            else:
                conflict = 'ON CONFLICT (id) DO NOTHING'
                
            insert_sql = f'INSERT INTO {table} ({insert_col_str}) VALUES ({placeholders}) {conflict}'
            
            for row in rows:
                tgt_cur.execute(insert_sql, row)
            
            tgt_conn.commit()
            processed_total += len(rows)
            logger.info(f"Successfully synced {len(rows)} rows to AWS table: {table}")
            
        return {"status": "success", "total_rows_synced": processed_total}
        
    except Exception as e:
        logger.error(f"AWS Sync failed: {e}")
        if tgt_conn: tgt_conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        if src_conn: src_conn.close()
        if tgt_conn: tgt_conn.close()


# =============================================
# CLEANUP TASK
# =============================================

@celery_app.task(name="app.tasks.celery_app.cleanup_old_articles")
def cleanup_old_articles():
    """Remove soft-deleted and old duplicate articles."""
    db = get_db()
    try:
        log = log_job(db, "cleanup")
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)

        deleted_count = db.query(NewsArticle).filter(
            NewsArticle.flag == "D",
            NewsArticle.updated_at < thirty_days_ago,
        ).delete(synchronize_session=False)

        dup_count = db.query(NewsArticle).filter(
            NewsArticle.is_duplicate == True,
            NewsArticle.created_at < thirty_days_ago,
        ).delete(synchronize_session=False)

        log_count = db.query(SchedulerLog).filter(
            SchedulerLog.started_at < ninety_days_ago,
        ).delete(synchronize_session=False)

        db.commit()
        total = deleted_count + dup_count + log_count
        complete_job(db, log, "completed", total)
        logger.info(f"[CLEANUP] {deleted_count} deleted, {dup_count} dups, {log_count} logs removed")
        return {"status": "success", "deleted": deleted_count, "duplicates": dup_count, "logs": log_count}
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


# =============================================
# FULL PIPELINE TASK
# =============================================

@celery_app.task(name="app.tasks.celery_app.run_full_pipeline")
def run_full_pipeline(source_id: int = None):
    """Cascaded pipeline: scrape â†’ AI â†’ ranking â†’ sync â†’ categories."""
    logger.info(f"[PIPELINE] Starting full pipeline (source_id={source_id})")
    results = {}
    try:
        if source_id:
            results["scrape"] = scrape_source(source_id)
        else:
            results["scrape"] = scrape_all_sources()
        results["ai"] = process_ai_batch()
        results["ranking"] = update_top_100_ranking()
        results["social"] = post_to_social()
        results["sync"] = sync_to_aws()
        results["categories"] = update_category_counts()
        logger.info(f"[PIPELINE] Complete")
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"[PIPELINE] Failed: {e}")
        return {"status": "error", "error": str(e), "partial": results}
