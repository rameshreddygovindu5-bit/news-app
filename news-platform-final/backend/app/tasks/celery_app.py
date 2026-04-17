"""
Celery Task Pipeline
====================
Order per cycle:
  1. scrape_all_sources     — pull raw articles
  2. process_ai_batch       — AI rephrase + category + Telugu
  3. update_top_100_ranking — score & mark top-100, guarantee ≥20/category
  4. sync_to_aws            — delta push to AWS production DB
  5. update_category_counts — refresh counts
  6. cleanup_old_articles   — soft-delete old content
  7. post_to_social         — FB/X/IG/WA for Y-flag articles
"""
import asyncio, logging, time, uuid, hashlib, re
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select, update, func, and_, text, desc
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SyncSessionLocal
from app.models.models import (
    NewsSource, NewsArticle, Category, JobExecutionLog,
    PostErrorLog, SyncMetadata, SourceErrorLog, Wish,
)
from app.scrapers.base_scraper import ScraperFactory
from app.services.ai_service import ai_service
from app.services.social_service import social_service

try:
    import psycopg2
except ImportError:
    psycopg2 = None

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Celery app ────────────────────────────────────────────────────────
celery_app = Celery("news_aggregator", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_serializer="json", accept_content=["json"], result_serializer="json",
    timezone="UTC", enable_utc=True, task_track_started=True,
    task_acks_late=True, worker_prefetch_multiplier=1,
    task_soft_time_limit=3600, task_time_limit=7200,
    broker_connection_retry_on_startup=True,
)

def _crontab(minutes_str: str) -> crontab:
    return crontab(minute=str(minutes_str))

def build_beat_schedule() -> dict:
    if not settings.SCHEDULER_ENABLED:
        return {}
    jobs = [
        ("scrape-all-sources",     settings.SCHEDULE_SCRAPE_ENABLED,         "app.tasks.celery_app.scrape_all_sources",     settings.SCHEDULE_SCRAPE_MINUTES),
        ("process-ai-batch",       settings.SCHEDULE_AI_ENABLED,             "app.tasks.celery_app.process_ai_batch",       settings.SCHEDULE_AI_MINUTES),
        ("update-top-100",         settings.SCHEDULE_RANKING_ENABLED,        "app.tasks.celery_app.update_top_100_ranking", settings.SCHEDULE_RANKING_MINUTES),
        ("sync-to-aws",            settings.SCHEDULE_AWS_SYNC_ENABLED,       "app.tasks.celery_app.sync_to_aws",            settings.SCHEDULE_AWS_SYNC_MINUTES),
        ("update-category-counts", settings.SCHEDULE_CATEGORY_COUNT_ENABLED, "app.tasks.celery_app.update_category_counts", settings.SCHEDULE_CATEGORY_MINUTES),
        ("cleanup-old-articles",   settings.SCHEDULE_CLEANUP_ENABLED,        "app.tasks.celery_app.cleanup_old_articles",   settings.SCHEDULE_CLEANUP_MINUTES),
        ("post-to-social",         settings.SCHEDULE_SOCIAL_ENABLED,         "app.tasks.celery_app.post_to_social",         settings.SCHEDULE_SOCIAL_MINUTES),
    ]
    schedule = {}
    for key, enabled, task, mins in jobs:
        if enabled:
            schedule[key] = {"task": task, "schedule": _crontab(mins)}
            logger.info(f"[SCHED] ON  ▶ {key:<32} @ {mins}")
        else:
            logger.info(f"[SCHED] OFF ■ {key}")
    return schedule

celery_app.conf.beat_schedule = build_beat_schedule()

# ── DB helper ────────────────────────────────────────────────────────
def get_db() -> Session: return SyncSessionLocal()

# ── Job lock ─────────────────────────────────────────────────────────
def log_job(db, job_name, triggered_by="cron"):
    run_id = str(uuid.uuid4())
    stale = datetime.now(timezone.utc) - timedelta(hours=2)
    db.execute(update(JobExecutionLog).where(JobExecutionLog.status=="RUNNING", JobExecutionLog.started_at<stale).values(status="FAILED", ended_at=func.now(), error_summary="Stale lock"))
    db.commit()
    
    # Check if already running
    running = db.query(JobExecutionLog).filter(JobExecutionLog.job_name==job_name, JobExecutionLog.status=="RUNNING").first()
    if running:
        logger.info(f"[JOB] {job_name} already running — skip")
        return None
    
    # Insert new job log (works with both SQLite and PostgreSQL)
    log_entry = JobExecutionLog(
        job_name=job_name, run_id=run_id,
        started_at=datetime.now(timezone.utc),
        status="RUNNING", triggered_by=triggered_by
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

def complete_job(db, log, ok, err, error_summary=None):
    if not log: return
    status = "DONE" if err==0 else ("PARTIAL" if ok>0 else "FAILED")
    log.status=status; log.rows_ok=ok; log.rows_err=err
    log.error_summary=error_summary; log.ended_at=datetime.now(timezone.utc)
    
    # Ensure aware comparison
    start = log.started_at; end = log.ended_at
    if start and start.tzinfo is None: start = start.replace(tzinfo=timezone.utc)
    if end and end.tzinfo is None: end = end.replace(tzinfo=timezone.utc)
    
    log.duration_s=(end-start).total_seconds()
    db.commit()
    logger.info(f"[JOB] {log.job_name} → {status} (ok={ok} err={err} {log.duration_s:.1f}s)")

def _banner(label, start=True):
    verb = "STARTING" if start else "DONE"
    logger.info(f"\n{'='*55}\n  {verb}: {label}\n  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n{'='*55}")

def normalize_title(t): return re.sub(r'[^\w\s]','',t.lower()).strip() if t else ""
def content_hash(source_id, title): return hashlib.sha256(f"{source_id}{normalize_title(title)}".encode()).hexdigest()

# ── TASK 1: SCRAPE ────────────────────────────────────────────────────
@celery_app.task(name="app.tasks.celery_app.scrape_all_sources")
def scrape_all_sources(ignore_window: bool = False):
    _banner("SCRAPE ALL SOURCES")
    db = get_db()
    log = log_job(db, "scrape_sources")
    if not log: return
    try:
        q = db.query(NewsSource).filter(NewsSource.is_enabled==True, NewsSource.is_paused==False)
        if settings.ENABLED_SOURCES:
            names = [s.strip().lower() for s in settings.ENABLED_SOURCES.split(",")]
            q = q.filter(func.lower(NewsSource.name).in_(names))
        sources = q.all()

        # Filter sources by time window (unless ignore_window=True)
        filtered_sources = []
        if ignore_window:
            filtered_sources = sources
        else:
            from datetime import timezone
            now_utc = datetime.now(timezone.utc)
            now_est_hour = (now_utc - timedelta(hours=5)).hour
            now_ist_hour = (now_utc + timedelta(hours=5, minutes=30)).hour
            
            for s in sources:
                name_l = s.name.lower()
                if "google" in name_l:
                    if 5 <= now_est_hour < 21: filtered_sources.append(s)
                    else: logger.info(f"[SCHED] Skipping {s.name} (Outside 5AM-9PM EST window)")
                else:
                    if 5 <= now_ist_hour < 21: filtered_sources.append(s)
                    else: logger.info(f"[SCHED] Skipping {s.name} (Outside 5AM-9PM IST window)")

        if not filtered_sources:
            complete_job(db, log, 0, 0, "No sources in active time window"); return
        
        ok = err = 0
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = {pool.submit(worker_scrape_source, s.id, log.run_id): s for s in filtered_sources}
            for f in as_completed(futures):
                r = f.result(); ok+=r.get("inserted",0); err+=r.get("errors",0)
        complete_job(db, log, ok, err)
    except Exception as e:
        logger.error(f"[SCRAPE] Fatal: {e}"); complete_job(db, log, 0, 1, str(e))
    finally:
        db.close()
    
    # Trigger sync after scrape complete
    try: sync_to_aws.delay()
    except: pass

    _banner("SCRAPE ALL SOURCES", False)

@celery_app.task(name="app.tasks.celery_app.scrape_source")
def scrape_source(source_id: int):
    db = get_db()
    try:
        src = db.query(NewsSource).get(source_id)
        if not src: return
        log = log_job(db, f"scrape_{src.name.lower()}", "manual")
        if not log: return
        r = worker_scrape_source(source_id, log.run_id)
        complete_job(db, log, r.get("inserted",0), r.get("errors",0))
    finally:
        db.close()

def worker_scrape_source(source_id: int, run_id: str) -> Dict:
    db = SyncSessionLocal()
    stats = {"inserted": 0, "errors": 0}
    try:
        src = db.query(NewsSource).get(source_id)
        if not src: return stats
        scraper = ScraperFactory.create({
            "name": src.name, "url": src.url,
            "scraper_type": src.scraper_type, "language": src.language,
            "scraper_config": src.scraper_config or {},
        })
        loop = asyncio.new_event_loop()
        try:
            articles = loop.run_until_complete(scraper.scrape())
        finally:
            loop.close()

        for a in articles:
            # Strip source names from content before storage
            from app.services.ai_service import _strip_source_names
            clean_title = _strip_source_names(a.title).strip()
            clean_content = _strip_source_names(a.content).strip()
            
            if not clean_content or len(clean_content) < 80:
                logger.warning(f"[SCRAPE] Skipping {src.name} article (insufficient content): {clean_title[:50]}")
                continue
            
            ch = content_hash(source_id, clean_title)
            if db.query(NewsArticle.id).filter(NewsArticle.content_hash==ch).first():
                continue
            is_dup = False; dup_id = None
            try:
                if "postgresql" in settings.DATABASE_URL_SYNC:
                    match = db.execute(text("SELECT id FROM news_articles WHERE created_at>NOW()-INTERVAL '48 hours' AND is_duplicate=FALSE AND similarity(original_title,:t)>0.85 LIMIT 1"), {"t": clean_title}).fetchone()
                else:
                    # SQLite fallback: exact title match within 2 days
                    match = db.execute(text("SELECT id FROM news_articles WHERE created_at>datetime('now','-2 days') AND is_duplicate=FALSE AND original_title=:t LIMIT 1"), {"t": clean_title}).fetchone()
                if match: is_dup=True; dup_id=match[0]
            except Exception: pass
            clean_slug = re.sub(r'[^\w\s-]','',clean_title.lower()).strip().replace(' ','-')[:100]
            slug = f"{clean_slug}-{hashlib.md5(a.url.encode()).hexdigest()[:6]}"
            new_art = NewsArticle(
                source_id=source_id,
                original_title=clean_title,
                original_content=clean_content or clean_title,
                original_url=a.url,
                original_language=src.language or "en",
                published_at=a.published_at or datetime.now(timezone.utc),
                image_url=a.image_url,
                content_hash=ch,
                is_duplicate=bool(is_dup),
                duplicate_of_id=dup_id,
                flag="N",
                ai_status="pending",
                ai_error_count=0, # Explicitly set for SQLite safety
                rephrased_title=clean_title,
                rephrased_content=clean_content,
                category=src.scraper_config.get("target_category", "Home"),
                slug=slug,
                scrape_metadata=a.metadata or {}
            )
            db.add(new_art); db.commit(); stats["inserted"] += 1
        src.last_scraped_at = datetime.now(timezone.utc); db.commit()
        logger.info(f"[SCRAPE] {src.name}: +{stats['inserted']}")
    except Exception as e:
        logger.error(f"[SCRAPE] Source {source_id}: {e}"); stats["errors"] = 1
    finally:
        db.close()
    return stats

# ── TASK 2: AI ENRICHMENT ─────────────────────────────────────────────
@celery_app.task(name="app.tasks.celery_app.process_ai_batch")
def process_ai_batch():
    _banner("AI ENRICHMENT")
    db = get_db()
    log = log_job(db, "ai_enrichment")
    if not log: return
    try:
        subq = db.query(NewsArticle.id).filter(NewsArticle.ai_status.in_(["pending","unknown"]), NewsArticle.is_duplicate==False).order_by(func.random()).limit(settings.AI_BATCH_SIZE).subquery()
        db.execute(update(NewsArticle).where(NewsArticle.id.in_(select(subq))).values(ai_status="processing"))
        db.commit()
        articles = db.query(NewsArticle).filter(NewsArticle.ai_status=="processing").all()
        if not articles:
            complete_job(db, log, 0, 0, "No pending"); return
        ok = err = 0
        with ThreadPoolExecutor(max_workers=min(settings.AI_CONCURRENCY, 8)) as pool:
            futures = [pool.submit(worker_process_ai, a.id) for a in articles]
            for f in as_completed(futures):
                if f.result(): ok+=1
                else: err+=1
        complete_job(db, log, ok, err)
    except Exception as e:
        logger.error(f"[AI] Fatal: {e}"); complete_job(db, log, 0, 1, str(e))
    finally:
        db.close()
    
    # Trigger sync after AI batch complete
    try: sync_to_aws.delay()
    except: pass

    _banner("AI ENRICHMENT", False)

def worker_process_ai(article_id: int) -> bool:
    db = SyncSessionLocal()
    try:
        art = db.query(NewsArticle).get(article_id)
        if not art: return False
        res = ai_service.process_article(art.original_title, art.original_content or "")
        art.rephrased_title = res["rephrased_title"]
        art.rephrased_content = res["rephrased_content"]
        art.telugu_title = res.get("telugu_title", "")
        art.telugu_content = res.get("telugu_content", "")
        art.category = res["category"]
        art.slug = res.get("slug") or art.slug
        art.tags = res.get("tags", [])
        art.ai_status = "completed"
        art.flag = "A"
        art.processed_at = datetime.now(timezone.utc)
        meta = dict(art.scrape_metadata or {}); meta["ai_method"] = res.get("method","unknown"); art.scrape_metadata = meta
        db.commit(); return True
    except Exception as e:
        logger.error(f"[AI] Article {article_id}: {e}")
        db.rollback()
        db.execute(update(NewsArticle).where(NewsArticle.id==article_id).values(ai_status="failed", ai_error_count=NewsArticle.ai_error_count+1))
        db.commit(); return False
    finally:
        db.close()

# ── TASK 3: TOP-100 RANKING ───────────────────────────────────────────
@celery_app.task(name="app.tasks.celery_app.update_top_100_ranking")
def update_top_100_ranking():
    _banner("TOP-100 RANKING")
    db = get_db()
    log = log_job(db, "ranking")
    if not log: return
    try:
        # Reset flags
        db.execute(update(NewsArticle).where(NewsArticle.flag=="Y").values(flag="A"))
        db.commit()

        # Find candidates — expand window until we have enough for 500 target
        candidates = []
        for days in [3, 7, 14, 30, 60]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            candidates = db.query(NewsArticle).join(NewsSource).filter(
                NewsArticle.ai_status=="completed",
                NewsArticle.created_at>=cutoff,
                NewsArticle.is_duplicate==False,
                NewsArticle.flag.in_(["A","Y"]),
            ).all()
            if len(candidates) >= settings.TOP_NEWS_COUNT: break

        if not candidates:
            # Ultimate fallback: get ALL completed non-duplicate articles ordered by recency
            candidates = db.query(NewsArticle).join(NewsSource).filter(
                NewsArticle.ai_status=="completed",
                NewsArticle.is_duplicate==False,
            ).order_by(desc(NewsArticle.created_at)).limit(settings.TOP_NEWS_COUNT * 2).all()
            logger.info(f"[RANK] Fallback candidates: {len(candidates)}")

        if not candidates:
            logger.warning("[RANK] No candidates found even in fallback!")
            complete_job(db, log, 0, 0, "No candidates"); return

        logger.info(f"[RANK] Scoring {len(candidates)} candidates")

        # Score
        now = datetime.now(timezone.utc)
        for a in candidates:
            # Handle naive datetime from SQLite or other sources
            cat = a.created_at
            if cat.tzinfo is None:
                cat = cat.replace(tzinfo=timezone.utc)
            
            age_h = (now - cat).total_seconds() / 3600
            a.rank_score = (a.source.priority*15) + (a.source.credibility_score*25) + max(0, 100-(0.4*age_h))
        db.commit()

        # Get categories
        all_cats = [r[0] for r in db.execute(select(Category.name)).all()]
        if not all_cats:
            all_cats = settings.CATEGORIES

        # Guarantee ≥ TOP_NEWS_MIN_PER_CATEGORY per category (fallback to 2-month window)
        two_months_ago = datetime.now(timezone.utc) - timedelta(days=60)
        final_ids: list[int] = []
        
        for cname in all_cats:
            cat_arts = sorted([a for a in candidates if a.category == cname], key=lambda x: x.rank_score or 0, reverse=True)
            
            # If fewer than MIN, supplement from 2-month window
            if len(cat_arts) < settings.TOP_NEWS_MIN_PER_CATEGORY:
                extra = db.query(NewsArticle).filter(
                    NewsArticle.category==cname,
                    NewsArticle.ai_status=="completed",
                    NewsArticle.is_duplicate==False,
                    NewsArticle.created_at>=two_months_ago,
                ).order_by(desc(NewsArticle.rank_score)).limit(settings.TOP_NEWS_MIN_PER_CATEGORY).all()
                seen = {a.id for a in cat_arts}
                for e in extra:
                    if e.id not in seen: cat_arts.append(e); seen.add(e.id)
                cat_arts = sorted(cat_arts, key=lambda x: x.rank_score or 0, reverse=True)

            take = max(settings.TOP_NEWS_MIN_PER_CATEGORY, min(settings.TOP_NEWS_MAX_PER_CATEGORY, len(cat_arts)))
            final_ids.extend(a.id for a in cat_arts[:take])

        # De-dup, sort, cap at TOP_NEWS_COUNT
        seen_ids: set[int] = set()
        unique_ids = []
        for aid in final_ids:
            if aid not in seen_ids:
                seen_ids.add(aid); unique_ids.append(aid)

        score_map = {a.id: (a.rank_score or 0) for a in candidates}
        top_ids = sorted(unique_ids, key=lambda aid: score_map.get(aid, 0), reverse=True)[:settings.TOP_NEWS_COUNT]

        if top_ids:
            db.execute(update(NewsArticle).where(NewsArticle.id.in_(top_ids)).values(flag="Y"))
            db.commit()

        complete_job(db, log, len(top_ids), 0)
        logger.info(f"[RANK] {len(top_ids)} articles marked as Top News")
    except Exception as e:
        db.rollback(); logger.error(f"[RANK] {e}"); complete_job(db, log, 0, 0, str(e))
    finally:
        db.close()
    
    # Trigger sync after Ranking complete
    try: sync_to_aws.delay()
    except: pass

    _banner("TOP-100 RANKING", False)

# ── TASK 4: AWS SYNC ──────────────────────────────────────────────────
@celery_app.task(name="app.tasks.celery_app.sync_to_aws")
def sync_to_aws():
    _banner("AWS SYNC")
    db = get_db()
    log = log_job(db, "aws_sync")
    if not log: return

    if not (settings.AWS_DB_HOST and settings.AWS_DB_USER and settings.AWS_DB_PASSWORD):
        complete_job(db, log, 0, 0, "AWS creds not configured")
        db.close(); return

    # Only sync to AWS when running locally (IS_LOCAL_DEV=true).
    # On EC2/AWS production, data is already in the production DB.
    if not settings.IS_LOCAL_DEV:
        complete_job(db, log, 0, 0, "Skipped — running on AWS (IS_LOCAL_DEV=false)")
        db.close(); return

    if psycopg2 is None:
        complete_job(db, log, 0, 0, "psycopg2 not installed — pip install psycopg2-binary")
        db.close(); return

    try:
        conn = psycopg2.connect(
            host=settings.AWS_DB_HOST, port=settings.AWS_DB_PORT,
            dbname=settings.AWS_DB_NAME, user=settings.AWS_DB_USER,
            password=settings.AWS_DB_PASSWORD, connect_timeout=15,
        )
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Ensure AWS has telugu columns
        for col, coltype in [("telugu_title", "TEXT"), ("telugu_content", "TEXT")]:
            try:
                cur.execute(f"ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS {col} {coltype};")
            except Exception: pass

        # 2. Categories
        local_cats = db.query(Category).all()
        local_cat_names = [c.name for c in local_cats]
        for c in local_cats:
            try:
                cur.execute("INSERT INTO categories (name,slug,description,is_active,article_count) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (name) DO UPDATE SET description=EXCLUDED.description,is_active=EXCLUDED.is_active,article_count=EXCLUDED.article_count",
                            (c.name, c.slug, c.description, c.is_active, c.article_count))
            except Exception as e: logger.warning(f"[AWS] Cat {c.name}: {e}")
        # Deactivate categories in AWS that are missing locally
        if local_cat_names:
            try: cur.execute("UPDATE categories SET is_active=FALSE WHERE name NOT IN %s", (tuple(local_cat_names),))
            except Exception: pass

        # 3. Sources
        local_sources = db.query(NewsSource).all()
        local_src_ids = [s.id for s in local_sources]
        enabled_local_ids = [s.id for s in local_sources if s.is_enabled]
        
        for s in local_sources:
            try:
                cur.execute("INSERT INTO news_sources (id,name,url,scraper_type,language,is_enabled,credibility_score,priority) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name,url=EXCLUDED.url,is_enabled=EXCLUDED.is_enabled,credibility_score=EXCLUDED.credibility_score,priority=EXCLUDED.priority",
                            (s.id,s.name,s.url,s.scraper_type,s.language,s.is_enabled,s.credibility_score,s.priority))
            except Exception as e: logger.warning(f"[AWS] Src {s.id}: {e}")
        
        # Pruning AWS data based on local source states
        try:
            # 1. Disable sources in AWS that are missing locally
            if local_src_ids:
                cur.execute("UPDATE news_sources SET is_enabled=FALSE WHERE id NOT IN %s", (tuple(local_src_ids),))
            
            # 2. Deactivate articles in AWS from sources that are NOT enabled locally
            if enabled_local_ids:
                cur.execute("UPDATE news_articles SET flag='D' WHERE source_id NOT IN %s AND flag != 'D'", (tuple(enabled_local_ids),))
            elif local_src_ids: # All sources disabled
                cur.execute("UPDATE news_articles SET flag='D' WHERE flag != 'D'")
        except Exception as e:
            logger.error(f"[AWS] Pruning Error: {e}")

        # 4. Wishes
        try:
            # Ensure table exists in AWS
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wishes (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    message TEXT,
                    wish_type VARCHAR(50) DEFAULT 'birthday',
                    person_name VARCHAR(255),
                    occasion_date TIMESTAMP WITH TIME ZONE,
                    image_url VARCHAR(1000),
                    is_active BOOLEAN DEFAULT TRUE,
                    display_on_home BOOLEAN DEFAULT FALSE,
                    likes_count INTEGER DEFAULT 0,
                    created_by VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP WITH TIME ZONE
                )
            """)
            # Ensure AWS wishes has likes_count column
            try: cur.execute("ALTER TABLE wishes ADD COLUMN IF NOT EXISTS likes_count INTEGER DEFAULT 0;")
            except Exception: pass

            local_wishes = db.query(Wish).all()
            local_wish_ids = [w.id for w in local_wishes]
            for w in local_wishes:
                cur.execute("""
                    INSERT INTO wishes (id, title, message, wish_type, person_name, occasion_date, image_url, is_active, display_on_home, likes_count, created_by, created_at, expires_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                        title=EXCLUDED.title, message=EXCLUDED.message, wish_type=EXCLUDED.wish_type, 
                        person_name=EXCLUDED.person_name, occasion_date=EXCLUDED.occasion_date, 
                        image_url=EXCLUDED.image_url, is_active=EXCLUDED.is_active, 
                        display_on_home=EXCLUDED.display_on_home, likes_count=EXCLUDED.likes_count, expires_at=EXCLUDED.expires_at
                """, (w.id, w.title, w.message, w.wish_type, w.person_name, w.occasion_date, w.image_url, w.is_active, w.display_on_home, w.likes_count, w.created_by, w.created_at, w.expires_at))
            
            # Deactivate wishes in AWS that are missing locally
            if local_wish_ids:
                cur.execute("UPDATE wishes SET is_active=FALSE WHERE id NOT IN %s", (tuple(local_wish_ids),))
        except Exception as e:
            logger.error(f"[AWS] Wishes Sync Error: {e}")

        # 5. Articles (delta)
        meta = db.query(SyncMetadata).filter(SyncMetadata.target=="AWS_PROD").first()
        if not meta:
            meta = SyncMetadata(target="AWS_PROD", last_sync_at=datetime.now(timezone.utc)-timedelta(days=7))
            db.add(meta); db.commit()

        records = db.query(NewsArticle).filter(NewsArticle.updated_at>meta.last_sync_at).all()
        if not records:
            cur.close(); conn.close()
            complete_job(db, log, 0, 0, "No delta"); return

        ok = err = 0
        sync_at = datetime.now(timezone.utc)
        import json
        SQL = """INSERT INTO news_articles (source_id,original_title,original_content,original_url,original_language,published_at,rephrased_title,rephrased_content,category,slug,tags,flag,image_url,author,content_hash,is_duplicate,duplicate_of_id,rank_score,telugu_title,telugu_content,created_at,updated_at)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                 ON CONFLICT (original_url) DO UPDATE SET
                   original_title=EXCLUDED.original_title, original_content=EXCLUDED.original_content,
                   rephrased_title=EXCLUDED.rephrased_title, rephrased_content=EXCLUDED.rephrased_content,
                   telugu_title=EXCLUDED.telugu_title, telugu_content=EXCLUDED.telugu_content,
                   category=EXCLUDED.category, slug=EXCLUDED.slug, tags=EXCLUDED.tags, flag=EXCLUDED.flag,
                   image_url=EXCLUDED.image_url, author=EXCLUDED.author, rank_score=EXCLUDED.rank_score,
                   updated_at=EXCLUDED.updated_at"""
        for art in records:
            try:
                # Type conversions for Postgres
                tags = art.tags
                if tags and isinstance(tags, str):
                    try: tags = json.loads(tags)
                    except: tags = []
                elif not tags:
                    tags = []
                
                cur.execute(SQL, (
                    art.source_id, art.original_title, art.original_content, art.original_url,
                    art.original_language, art.published_at, art.rephrased_title, art.rephrased_content,
                    art.category, art.slug, tags, art.flag, art.image_url, art.author,
                    art.content_hash, bool(art.is_duplicate), art.duplicate_of_id, art.rank_score,
                    getattr(art,'telugu_title',''), getattr(art,'telugu_content',''),
                    art.created_at, art.updated_at,
                ))
                ok += 1
            except Exception as e:
                # If slug collision on a new URL, try appending suffix
                if "slug" in str(e).lower() and "unique" in str(e).lower():
                    try:
                        new_slug = f"{art.slug}-{uuid.uuid4().hex[:4]}"
                        cur.execute(SQL, (
                            art.source_id, art.original_title, art.original_content, art.original_url,
                            art.original_language, art.published_at, art.rephrased_title, art.rephrased_content,
                            art.category, new_slug, tags, art.flag, art.image_url, art.author,
                            art.content_hash, bool(art.is_duplicate), art.duplicate_of_id, art.rank_score,
                            getattr(art,'telugu_title',''), getattr(art,'telugu_content',''),
                            art.created_at, art.updated_at,
                        ))
                        ok += 1; continue
                    except: pass
                logger.error(f"[AWS] Art {art.id}: {e}"); err += 1

        cur.close(); conn.close()
        meta.last_sync_at=sync_at; meta.last_rows_ok=ok; meta.last_rows_err=err; db.commit()
        complete_job(db, log, ok, err)
        logger.info(f"[AWS] Synced {ok} ok, {err} err")
    except Exception as e:
        logger.error(f"[AWS] Fatal: {e}"); complete_job(db, log, 0, 0, str(e))
    finally:
        db.close()
    _banner("AWS SYNC", False)
    _banner("AWS SYNC", False)

# ── TASK 5: CATEGORY COUNTS ───────────────────────────────────────────
@celery_app.task(name="app.tasks.celery_app.update_category_counts")
def update_category_counts():
    db = get_db()
    try:
        if "postgresql" in settings.DATABASE_URL_SYNC:
            db.execute(text("UPDATE categories c SET article_count=(SELECT COUNT(*) FROM news_articles a WHERE a.category=c.name AND a.flag!='D')"))
        else:
            db.execute(text("UPDATE categories SET article_count=(SELECT COUNT(*) FROM news_articles WHERE news_articles.category=categories.name AND news_articles.flag!='D')"))
        db.commit(); logger.info("[CATS] Counts refreshed")
    except Exception as e: logger.error(f"[CATS] {e}")
    finally: db.close()

# ── TASK 6: CLEANUP ───────────────────────────────────────────────────
@celery_app.task(name="app.tasks.celery_app.cleanup_old_articles")
def cleanup_old_articles():
    db = get_db()
    log = log_job(db, "maintenance")
    if not log: return
    try:
        res = db.execute(update(NewsArticle).where(NewsArticle.created_at<datetime.now(timezone.utc)-timedelta(days=15), NewsArticle.flag!="D").values(flag="D", deleted_at=func.now()))
        db.commit(); complete_job(db, log, res.rowcount, 0)
    except Exception as e: logger.error(f"[CLEANUP] {e}"); complete_job(db, log, 0, 0, str(e))
    finally: db.close()

# ── TASK 7: SOCIAL POSTING ────────────────────────────────────────────
@celery_app.task(name="app.tasks.celery_app.post_to_social")
def post_to_social():
    _banner("SOCIAL POSTING")
    db = get_db()
    log = log_job(db, "social_post")
    if not log: return
    try:
        unposted = db.query(NewsArticle).filter(
            NewsArticle.flag=="Y", NewsArticle.is_posted_fb==False
        ).order_by(NewsArticle.rank_score.desc()).limit(10).all()
        posted = 0
        for art in unposted:
            try:
                url = f"{settings.SOCIAL_SITE_URL}/news/{art.slug or art.id}"
                title = art.rephrased_title or art.original_title
                results = social_service.post_to_all(art.id, title, art.rephrased_content or "", url)
                # Mark posted regardless (prevent retry spam if partially posted)
                art.is_posted_fb = True; art.is_posted_ig = True
                art.is_posted_x = True; art.is_posted_wa = True
                posted += 1
            except Exception as e:
                logger.warning(f"[SOCIAL] Art {art.id}: {e}")
        db.commit(); complete_job(db, log, posted, 0)
        logger.info(f"[SOCIAL] Posted {posted} articles")
    except Exception as e:
        logger.error(f"[SOCIAL] {e}"); complete_job(db, log, 0, 0, str(e))
    finally: db.close()
    _banner("SOCIAL POSTING", False)

# ── FULL PIPELINE ─────────────────────────────────────────────────────
@celery_app.task(name="app.tasks.celery_app.run_full_pipeline")
def run_full_pipeline(source_id: Optional[int] = None):
    _banner("FULL PIPELINE")
    t0 = time.time()
    logger.info("[PIPELINE] 1/6 Scrape...")
    if source_id: scrape_source(source_id)
    else: scrape_all_sources()
    logger.info("[PIPELINE] 2/6 AI...")
    process_ai_batch()
    logger.info("[PIPELINE] 3/6 Ranking...")
    update_top_100_ranking()
    logger.info("[PIPELINE] 4/6 AWS Sync...")
    sync_to_aws()
    logger.info("[PIPELINE] 5/6 Category Counts...")
    update_category_counts()
    logger.info("[PIPELINE] 6/6 Social...")
    post_to_social()
    logger.info(f"[PIPELINE] Complete in {time.time()-t0:.1f}s")
    _banner("FULL PIPELINE", False)

if __name__ == "__main__":
    import sys
    cmds = {
        "--run": run_full_pipeline, "--scrape": scrape_all_sources,
        "--ai": process_ai_batch, "--rank": update_top_100_ranking,
        "--aws": sync_to_aws, "--social": post_to_social,
        "--cleanup": cleanup_old_articles, "--cats": update_category_counts,
    }
    if len(sys.argv)>1 and sys.argv[1] in cmds:
        cmds[sys.argv[1]]()
    else:
        print("Usage: python -m app.tasks.celery_app", "|".join(cmds))
