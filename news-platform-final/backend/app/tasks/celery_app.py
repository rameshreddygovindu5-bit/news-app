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
    PostErrorLog, SyncMetadata, SourceErrorLog, Wish, PollOption,
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
        ("master-news-heartbeat",  True,                                     "app.tasks.celery_app.run_master_heartbeat",   "*/10"),
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
    
    # Check if already running (Skip lock for aws_sync to allow real-time API triggers)
    if not job_name.startswith("aws_sync"):
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
    logger.info(f"\n{'━'*60}\n  {verb}: {label}\n  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n{'━'*60}")

def normalize_title(t): return re.sub(r'[^\w\s]','',t.lower()).strip() if t else ""
def content_hash(source_id, title): return hashlib.sha256(f"{source_id}{normalize_title(title)}".encode()).hexdigest()

def _trigger_full_pipeline():
    """Trigger the coordinated master heartbeat to ensure all stages (AI -> Rank -> Sync) run in order."""
    try:
        run_master_heartbeat.delay()
        logger.info("[PIPELINE] Master Heartbeat triggered via Celery")
    except Exception as e:
        import threading
        logger.warning(f"[PIPELINE] Celery delay failed ({e}) — falling back to thread")
        threading.Thread(target=run_master_heartbeat, daemon=True).start()


def trigger_immediate_sync():
    """Trigger a lightweight immediate AWS sync (article mutations: create/update/delete).
    Runs in background thread so it never blocks the API response."""
    import threading
    def _sync():
        try:
            sync_to_aws()
        except Exception as e:
            logger.warning(f"[SYNC] Immediate sync failed: {e}")
    try:
        sync_to_aws.delay()
    except Exception:
        threading.Thread(target=_sync, daemon=True).start()

# ── TASK 1: SCRAPE ────────────────────────────────────────────────────
@celery_app.task(name="app.tasks.celery_app.scrape_all_sources")
def scrape_all_sources(ignore_window: bool = False):
    _banner("SCRAPE ALL SOURCES")
    db = get_db()
    log = log_job(db, "scrape_sources")
    if not log: return
    # Skip scraping on AWS (Local is master)
    if not settings.IS_LOCAL_DEV:
        complete_job(db, log, 0, 0, "Skipped on AWS")
        db.close(); return
    try:
        q = db.query(NewsSource).filter(NewsSource.is_enabled==True, NewsSource.is_paused==False)
        if settings.ENABLED_SOURCES:
            names = [s.strip().lower() for s in settings.ENABLED_SOURCES.split(",")]
            q = q.filter(func.lower(NewsSource.name).in_(names))
        sources = q.all()

        # Filter sources by time window - removed for 24/7 automation
        filtered_sources = sources

        if not filtered_sources:
            complete_job(db, log, 0, 0, "No sources in active time window"); return
        
        ok = err = 0
        with ThreadPoolExecutor(max_workers=min(settings.AI_CONCURRENCY, 8)) as pool:
            futures = {pool.submit(worker_scrape_source, s.id, log.run_id): s for s in filtered_sources}
            for f in as_completed(futures):
                r = f.result(); ok+=r.get("inserted",0); err+=r.get("errors",0)
        complete_job(db, log, ok, err)
    except Exception as e:
        logger.error(f"[SCRAPE] Fatal: {e}"); complete_job(db, log, 0, 1, str(e))
    finally:
        db.close()
    
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
    # Skip AI processing on AWS (Local is master)
    if not settings.IS_LOCAL_DEV:
        complete_job(db, log, 0, 0, "Skipped on AWS")
        db.close(); return
    try:
        # STEP 0: Reset ALL stuck "processing" articles — key fix for the 353 stuck bug.
        # Articles stuck in "processing" were picked by a previous batch that crashed.
        # ANY article still "processing" after >5 min must be re-queued.
        stuck_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        stuck_reset = db.execute(
            update(NewsArticle)
            .where(
                NewsArticle.ai_status == "processing",
                NewsArticle.updated_at < stuck_cutoff
            )
            .values(ai_status="pending", updated_at=func.now())
        )
        if stuck_reset.rowcount:
            logger.info(f"[AI] Reset {stuck_reset.rowcount} stuck 'processing' → pending")
        db.commit()

        # STEP 1: Fetch pending IDs as Python list (avoids SQLAlchemy subquery cache bug)
        pending_rows = db.execute(
            select(NewsArticle.id)
            .where(
                NewsArticle.ai_status.in_(["pending", "unknown"]),
                NewsArticle.is_duplicate == False,
            )
            .order_by(func.random())
            .limit(settings.AI_BATCH_SIZE)
        ).fetchall()

        if not pending_rows:
            logger.info("[AI] No pending articles in this batch — all up to date")
            complete_job(db, log, 0, 0, "No pending articles")
            return

        article_ids = [row[0] for row in pending_rows]
        logger.info(f"[AI] Processing batch of {len(article_ids)} articles")

        # STEP 2: Mark exactly those IDs as "processing" (no subquery — direct IN list)
        db.execute(
            update(NewsArticle)
            .where(NewsArticle.id.in_(article_ids))
            .values(ai_status="processing", updated_at=func.now())
        )
        db.commit()

        # STEP 3: Process each article in parallel threads
        ok = err = 0
        with ThreadPoolExecutor(max_workers=min(settings.AI_CONCURRENCY, 8)) as pool:
            futures = {pool.submit(worker_process_ai, aid): aid for aid in article_ids}
            for future in as_completed(futures, timeout=300):  # 5-min max per batch
                try:
                    if future.result(timeout=120):  # 2-min max per article
                        ok += 1
                    else:
                        err += 1
                except TimeoutError:
                    logger.warning("[AI] Worker timed out — article reset to pending")
                    err += 1
                except Exception as ex:
                    logger.error(f"[AI] Worker exception: {ex}")
                    err += 1

        complete_job(db, log, ok, err)
        # Auto-trigger ranking and sync immediately after AI batch completes
        if ok > 0:
            try:
                import threading
                def _auto_rank_sync():
                    try:
                        update_top_100_ranking()
                        sync_to_aws()
                    except Exception as ae:
                        logger.warning(f"[AI→RANK→SYNC] auto chain failed: {ae}")
                threading.Thread(target=_auto_rank_sync, daemon=True).start()
                logger.info(f"[AI] Auto-triggered Ranking+Sync for {ok} processed articles")
            except Exception: pass
    except Exception as e:
        logger.error(f"[AI] Fatal: {e}", exc_info=True)
        complete_job(db, log, 0, 1, str(e))
        # Reset any articles left as "processing" from this failed batch
        try:
            db.execute(
                update(NewsArticle)
                .where(NewsArticle.ai_status == "processing")
                .values(ai_status="pending", updated_at=func.now())
            )
            db.commit()
        except Exception:
            pass
    finally:
        db.close()

    _banner("AI ENRICHMENT", False)

def worker_process_ai(article_id: int) -> bool:
    db = SyncSessionLocal()
    try:
        art = db.get(NewsArticle, article_id)  # SQLAlchemy 2.0 API (replaces deprecated .get())
        if not art: return False
        
        # New: Pass source name for specific fallback rules
        source_name = art.source.name if art.source else "Unknown"
        res = ai_service.process_article(art.original_title, art.original_content or "", source_name=source_name)
        
        # Ensure rephrased fields are never empty, strip source names for copyright
        from app.services.ai_service import _strip_source_names
        raw_reph_title = _strip_source_names(res.get("rephrased_title") or art.original_title or "")
        # If rephrased title is identical to original, force a stronger rephrase
        orig_normalized = (art.original_title or "").strip().lower()
        reph_normalized = raw_reph_title.strip().lower()
        if orig_normalized == reph_normalized and len(raw_reph_title.split()) >= 4:
            try:
                from app.services.paraphrase.fast_engine import rephrase_title
                import hashlib
                seed = int(hashlib.md5(raw_reph_title[:40].encode()).hexdigest()[:6], 16) % 10000
                forced = rephrase_title(raw_reph_title, seed=seed + 999)  # different seed
                if forced.strip().lower() != orig_normalized:
                    raw_reph_title = forced
            except Exception:
                pass
        art.rephrased_title = raw_reph_title
        art.rephrased_content = res.get("rephrased_content") or art.original_content or ""
        art.telugu_title = res.get("telugu_title", "")
        art.telugu_content = res.get("telugu_content", "")
        
        # Priority Category Logic: Respect source-defined target category if not "Home"
        target_cat = art.source.scraper_config.get("target_category") if art.source and art.source.scraper_config else None
        if target_cat and target_cat not in ["Home", "General"]:
            art.category = target_cat
        else:
            art.category = res["category"]

        new_slug = res.get("slug", "")
        if new_slug and len(new_slug) > 3:
            art.slug = new_slug
        art.tags = res.get("tags", [])
        art.image_url = res.get("image_url", art.image_url)
        
        # Use specific status code
        # Valid: AI_SUCCESS, AI_RETRY_SUCCESS, UNPROCESSED_AI_FALLBACK, GOOGLE_NEWS_NO_AI, REWRITE_FAILED
        status_code = res.get("ai_status_code", "completed")
        art.ai_status = status_code
        
        # STRICT: every processed article gets flag=A regardless of which engine ran.
        # LOCAL_PARAPHRASE = structured HTML from local engine (publicly visible)
        # AI_SUCCESS/AI_RETRY_SUCCESS = processed by Gemini/Grok/OpenAI (best quality)
        # GOOGLE_NEWS_NO_AI = cleaned original (publicly visible)
        art.flag = "A"
        engine = "cloud AI" if status_code in ("AI_SUCCESS","AI_RETRY_SUCCESS") else "local engine"
        logger.info(f"[AI] Article {article_id} → flag=A via {engine} ({status_code})")

        # Update image_url based on USE_CUSTOM_IMAGES setting
        if settings.USE_CUSTOM_IMAGES:
            # Always use branded category placeholder
            cat = art.category or "Home"
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
            art.image_url = _CAT_IMG.get(cat, "/placeholders/general.png")
        # else: keep existing scraped image_url
            
        art.processed_at = datetime.now(timezone.utc)
        
        # Metadata
        meta = dict(art.scrape_metadata or {})
        meta["ai_method"] = res.get("method","unknown")
        meta["ai_status_detail"] = status_code
        meta["similarity_score"] = res.get("similarity_score", 1.0)
        art.scrape_metadata = meta
        
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
    # Skip ranking on AWS (Local is master)
    if not settings.IS_LOCAL_DEV:
        complete_job(db, log, 0, 0, "Skipped on AWS")
        db.close(); return
    try:
        # Reset flags - MUST update updated_at so sync picks up the change
        db.execute(update(NewsArticle).where(NewsArticle.flag=="Y").values(flag="A", updated_at=func.now()))
        db.commit()

        # Find candidates — expand window until we have enough for 500 target
        candidates = []
        for days in [3, 7, 14, 30, 60]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            candidates = db.query(NewsArticle).join(NewsSource).filter(
                NewsArticle.ai_status.in_([
                    "completed", "AI_SUCCESS", "AI_RETRY_SUCCESS",
                    "UNPROCESSED_AI_FALLBACK", "GOOGLE_NEWS_NO_AI",
                    "GOOGLE_NEWS_LOCAL", "LOCAL_PARAPHRASE"
                ]),
                NewsArticle.created_at>=cutoff,
                NewsArticle.is_duplicate==False,
                NewsArticle.flag.in_(["A","Y"]),
            ).all()
            if len(candidates) >= settings.TOP_NEWS_COUNT: break

        if not candidates:
            # Ultimate fallback: get ALL completed non-duplicate articles ordered by recency
            candidates = db.query(NewsArticle).join(NewsSource).filter(
                NewsArticle.ai_status.in_([
                    "completed", "AI_SUCCESS", "AI_RETRY_SUCCESS",
                    "UNPROCESSED_AI_FALLBACK", "GOOGLE_NEWS_NO_AI",
                    "GOOGLE_NEWS_LOCAL", "LOCAL_PARAPHRASE"
                ]),
                NewsArticle.is_duplicate==False,
            ).order_by(desc(NewsArticle.created_at)).limit(settings.TOP_NEWS_COUNT * 2).all()  # Fetch 2× then trim to TOP_NEWS_COUNT=200
            logger.info(f"[RANK] Fallback candidates: {len(candidates)}")

        if not candidates:
            logger.warning("[RANK] No candidates found even in fallback!")
            complete_job(db, log, 0, 0, "No candidates"); return

        logger.info(f"[RANK] Scoring {len(candidates)} candidates")

        # Score - Prioritize recency for 'Latest News' feel
        now = datetime.now(timezone.utc)
        for a in candidates:
            cat = a.published_at or a.created_at
            if cat.tzinfo is None: cat = cat.replace(tzinfo=timezone.utc)
            
            age_h = (now - cat).total_seconds() / 3600
            # Higher recency weight: 1000 - (20 * age_h) ensures fresh news stays above old high-priority sources
            recency_score = max(0, 1000 - (20 * age_h)) 
            a.rank_score = (a.source.priority * 10) + (a.source.credibility_score * 20) + recency_score
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
                    NewsArticle.ai_status.in_(["completed","AI_SUCCESS","AI_RETRY_SUCCESS","UNPROCESSED_AI_FALLBACK","GOOGLE_NEWS_NO_AI","GOOGLE_NEWS_LOCAL","LOCAL_PARAPHRASE","REWRITE_FAILED"]),
                    NewsArticle.is_duplicate==False,
                    NewsArticle.created_at>=two_months_ago,
                ).order_by(desc(NewsArticle.rank_score)).limit(settings.TOP_NEWS_MIN_PER_CATEGORY).all()
                seen = {a.id for a in cat_arts}
                for e in extra:
                    if e.id not in seen: cat_arts.append(e); seen.add(e.id)
                cat_arts = sorted(cat_arts, key=lambda x: (x.rank_score or 0), reverse=True)

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
            db.execute(update(NewsArticle).where(NewsArticle.id.in_(top_ids)).values(flag="Y", updated_at=func.now()))
            db.commit()

        complete_job(db, log, len(top_ids), 0)
        logger.info(f"[RANK] {len(top_ids)} articles marked as Top News")
    except Exception as e:
        db.rollback(); logger.error(f"[RANK] {e}"); complete_job(db, log, 0, 0, str(e))
    finally:
        db.close()
    
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

        # 6. Polls
        try:
            # Tables exist?
            cur.execute("CREATE TABLE IF NOT EXISTS polls (id SERIAL PRIMARY KEY, question VARCHAR(500) NOT NULL, description TEXT, is_active BOOLEAN DEFAULT TRUE, expires_at TIMESTAMP WITH TIME ZONE, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);")
            cur.execute("CREATE TABLE IF NOT EXISTS poll_options (id SERIAL PRIMARY KEY, poll_id INTEGER REFERENCES polls(id) ON DELETE CASCADE, option_text VARCHAR(255) NOT NULL, votes_count INTEGER DEFAULT 0);")
            
            from app.models.models import Poll, PollOption
            local_polls = db.query(Poll).all()
            local_poll_ids = [p.id for p in local_polls]
            for p in local_polls:
                cur.execute("INSERT INTO polls (id,question,description,is_active,expires_at,created_at) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET question=EXCLUDED.question,description=EXCLUDED.description,is_active=EXCLUDED.is_active,expires_at=EXCLUDED.expires_at",
                            (p.id, p.question, p.description, p.is_active, p.expires_at, p.created_at))
            
            # Options
            local_options = db.query(PollOption).all()
            local_opt_ids = [o.id for o in local_options]
            for o in local_options:
                cur.execute("INSERT INTO poll_options (id,poll_id,option_text,votes_count) VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET option_text=EXCLUDED.option_text,votes_count=EXCLUDED.votes_count",
                            (o.id, o.poll_id, o.option_text, o.votes_count))
            
            # Prune
            if local_poll_ids: cur.execute("UPDATE polls SET is_active=FALSE WHERE id NOT IN %s", (tuple(local_poll_ids),))
            if local_opt_ids: cur.execute("DELETE FROM poll_options WHERE id NOT IN %s", (tuple(local_opt_ids),))

            # ── Bidirectional: pull AWS vote counts back to local DB ──────────
            # AWS is the authoritative source for votes (public users vote on AWS)
            try:
                if local_opt_ids:
                    cur.execute(
                        "SELECT id, votes_count FROM poll_options WHERE id = ANY(%s)",
                        (list(local_opt_ids),)
                    )
                    aws_votes = cur.fetchall()
                    for aws_id, aws_count in aws_votes:
                        db.execute(
                            update(PollOption).where(PollOption.id == aws_id).values(votes_count=aws_count)
                        )
                    if aws_votes:
                        db.commit()
                        logger.info(f"[AWS] Pulled vote counts for {len(aws_votes)} poll options from AWS → local")
            except Exception as ev:
                logger.warning(f"[AWS] Vote pull-back failed (non-critical): {ev}")
        except Exception as e:
            logger.error(f"[AWS] Polls Sync Error: {e}")

        # 7. Articles (delta)
        meta = db.query(SyncMetadata).filter(SyncMetadata.target=="AWS_PROD").first()
        if not meta:
            meta = SyncMetadata(target="AWS_PROD", last_sync_at=datetime.now(timezone.utc)-timedelta(days=7))
            db.add(meta); db.commit()

        # 2-minute overlap to ensure no record missed during sync transitions
        sync_cutoff = meta.last_sync_at - timedelta(minutes=2)
        
        # Always sync Top News (flag=Y) updated in last 7 days — critical for homepage
        high_priority_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        
        records = db.query(NewsArticle).filter(
            (NewsArticle.updated_at > sync_cutoff) | 
            ((NewsArticle.flag == "Y") & (NewsArticle.updated_at > high_priority_cutoff))
        ).all()
        
        if not records:
            # Even with no new articles, ensure categories/sources are up to date
            logger.info("[AWS] No new article delta — skipping article sync (categories/sources already synced)")
            cur.close(); conn.close()
            meta.last_sync_at = datetime.now(timezone.utc); db.commit()
            complete_job(db, log, 0, 0, "No article delta — metadata synced")
            db.close(); return

        ok = err = 0
        sync_at = datetime.now(timezone.utc)
        import json
        SQL = """INSERT INTO news_articles (source_id,original_title,original_content,original_url,original_language,published_at,rephrased_title,rephrased_content,category,slug,tags,flag,image_url,author,content_hash,is_duplicate,duplicate_of_id,rank_score,telugu_title,telugu_content,ai_status,processed_at,ai_error_count,created_at,updated_at)
                 VALUES %s
                 ON CONFLICT (original_url) DO UPDATE SET
                   original_title=EXCLUDED.original_title, original_content=EXCLUDED.original_content,
                   rephrased_title=EXCLUDED.rephrased_title, rephrased_content=EXCLUDED.rephrased_content,
                   telugu_title=EXCLUDED.telugu_title, telugu_content=EXCLUDED.telugu_content,
                   category=EXCLUDED.category, slug=EXCLUDED.slug, tags=EXCLUDED.tags, flag=EXCLUDED.flag,
                   image_url=EXCLUDED.image_url, author=EXCLUDED.author, rank_score=EXCLUDED.rank_score,
                   ai_status=EXCLUDED.ai_status, processed_at=EXCLUDED.processed_at, 
                   ai_error_count=EXCLUDED.ai_error_count, updated_at=EXCLUDED.updated_at"""
        from psycopg2.extras import execute_values
        
        # Prepare list of tuples for bulk execution
        data_to_sync = []
        for art in records:
            tags = art.tags
            if tags and isinstance(tags, str):
                try: tags = json.loads(tags)
                except: tags = []
            elif not tags:
                tags = []
            
            data_to_sync.append((
                art.source_id, art.original_title, art.original_content, art.original_url,
                art.original_language, art.published_at, art.rephrased_title, art.rephrased_content,
                art.category, art.slug, tags, art.flag, art.image_url, art.author,
                art.content_hash, bool(art.is_duplicate), art.duplicate_of_id, art.rank_score,
                getattr(art,'telugu_title',''), getattr(art,'telugu_content',''),
                art.ai_status, art.processed_at, art.ai_error_count,
                art.created_at, art.updated_at,
            ))

        # Bulk execute with ON CONFLICT support
        try:
            execute_values(cur, SQL, data_to_sync)
            ok = len(data_to_sync)
        except Exception as e:
            logger.warning(f"[AWS] Bulk sync failed ({e}) — falling back to sequential")
            conn.rollback() # Rollback the failed bulk attempt
            ok = err = 0
            # Define sequential SQL with individual placeholders
            SQL_SINGLE = SQL.replace("VALUES %s", "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)")
            for art in records:
                try:
                    tags = art.tags
                    if tags and isinstance(tags, str):
                        try: tags = json.loads(tags)
                        except: tags = []
                    elif not tags:
                        tags = []
                    
                    cur.execute(SQL_SINGLE, (
                        art.source_id, art.original_title, art.original_content, art.original_url,
                        art.original_language, art.published_at, art.rephrased_title, art.rephrased_content,
                        art.category, art.slug, tags, art.flag, art.image_url, art.author,
                        art.content_hash, bool(art.is_duplicate), art.duplicate_of_id, art.rank_score,
                        getattr(art,'telugu_title',''), getattr(art,'telugu_content',''),
                        art.ai_status, art.processed_at, art.ai_error_count,
                        art.created_at, art.updated_at,
                    ))
                    ok += 1
                except Exception as e2:
                    logger.error(f"[AWS] Art {art.id} sequential FAIL: {e2}")
                    err += 1

        cur.close(); conn.close()
        meta.last_sync_at=sync_at; meta.last_rows_ok=ok; meta.last_rows_err=err; db.commit()
        complete_job(db, log, ok, err)
        logger.info(f"[AWS] Synced {ok} ok, {err} err")

        # 8. Pruning: Sync Deletions
        try:
            conn = psycopg2.connect(host=settings.AWS_DB_HOST, port=settings.AWS_DB_PORT, dbname=settings.AWS_DB_NAME, user=settings.AWS_DB_USER, password=settings.AWS_DB_PASSWORD)
            cur = conn.cursor()
            
            # Deletions (Local flag 'D' -> Remote flag 'D')
            deleted_locally = db.query(NewsArticle.original_url).filter(NewsArticle.flag == "D").all()
            if deleted_locally:
                deleted_urls = [r[0] for r in deleted_locally]
                # Update in chunks of 500
                for i in range(0, len(deleted_urls), 500):
                    chunk = deleted_urls[i:i+500]
                    cur.execute("UPDATE news_articles SET flag='D' WHERE original_url IN %s", (tuple(chunk),))
                conn.commit()
            
            # Physical Cleanup (If it doesn't exist locally at all, hide it in AWS)
            # We don't want to delete from AWS if it's just 'archived' locally, but the user expects SYNC.
            cur.close(); conn.close()
        except Exception as e:
            logger.error(f"[AWS] Pruning Error: {e}")
    except Exception as e:
        logger.error(f"[AWS] Fatal: {e}"); complete_job(db, log, 0, 0, str(e))
    finally:
        db.close()
    _banner("AWS SYNC", False)


@celery_app.task(name="app.tasks.celery_app.full_integrity_sync")
def full_integrity_sync():
    """Nuclear option sync: Checks every single active local article against AWS."""
    _banner("FULL INTEGRITY SYNC")
    db = get_db()
    log = log_job(db, "full_integrity_sync", "manual")
    if not log: return

    if not (settings.AWS_DB_HOST and settings.AWS_DB_USER and settings.AWS_DB_PASSWORD):
        complete_job(db, log, 0, 0, "AWS creds not configured")
        db.close(); return

    try:
        # 1. First, call the standard sync_to_aws logic (base sync)
        # This handles categories, sources, wishes, polls
        sync_to_aws()
        
        # 2. Now perform the deep article scan
        conn = psycopg2.connect(host=settings.AWS_DB_HOST, port=settings.AWS_DB_PORT, dbname=settings.AWS_DB_NAME, user=settings.AWS_DB_USER, password=settings.AWS_DB_PASSWORD)
        cur = conn.cursor()
        
        # Get ALL local URLs
        all_local = db.query(NewsArticle).filter(NewsArticle.flag != "D").all()
        total_count = len(all_local)
        ok = err = 0
        
        SQL = """INSERT INTO news_articles (source_id,original_title,original_content,original_url,original_language,published_at,rephrased_title,rephrased_content,category,slug,tags,flag,image_url,author,content_hash,is_duplicate,duplicate_of_id,rank_score,telugu_title,telugu_content,ai_status,processed_at,ai_error_count,created_at,updated_at)
                 VALUES %s
                 ON CONFLICT (original_url) DO UPDATE SET
                   flag=EXCLUDED.flag, category=EXCLUDED.category, rank_score=EXCLUDED.rank_score,
                   telugu_title=EXCLUDED.telugu_title, telugu_content=EXCLUDED.telugu_content,
                   updated_at=EXCLUDED.updated_at"""
        
        from psycopg2.extras import execute_values
        import json
        
        # Process in chunks - PASS 1: Base data (no foreign key for duplicates yet)
        for i in range(0, total_count, 500):
            chunk = all_local[i : i + 500]
            data_to_sync = []
            for art in chunk:
                tags = art.tags
                if tags and isinstance(tags, str):
                    try: tags = json.loads(tags)
                    except: tags = []
                elif not tags: tags = []
                
                data_to_sync.append((
                    art.source_id, art.original_title, art.original_content, art.original_url,
                    art.original_language, art.published_at, art.rephrased_title, art.rephrased_content,
                    art.category, art.slug, tags, art.flag, art.image_url, art.author,
                    art.content_hash, bool(art.is_duplicate), None, art.rank_score, # Pass None for duplicate_of_id
                    getattr(art,'telugu_title',''), getattr(art,'telugu_content',''),
                    art.ai_status, art.processed_at, art.ai_error_count,
                    art.created_at, art.updated_at,
                ))
            
            try:
                execute_values(cur, SQL, data_to_sync)
                ok += len(data_to_sync)
                conn.commit()
            except Exception as e:
                logger.error(f"[INTEGRITY-P1] Chunk {i} failed: {e}")
                conn.rollback(); err += len(data_to_sync)

        # PASS 2: Link duplicates (now that all URLs exist on AWS)
        if ok > 0:
            logger.info("[INTEGRITY] PASS 2: Linking duplicates...")
            dupes = [a for a in all_local if a.duplicate_of_id]
            for d in dupes:
                try:
                    # Get the parent URL locally
                    parent = db.query(NewsArticle).filter(NewsArticle.id == d.duplicate_of_id).first()
                    if parent:
                        # Find parent ID on AWS by URL
                        cur.execute("SELECT id FROM news_articles WHERE original_url = %s", (parent.original_url,))
                        aws_parent = cur.fetchone()
                        if aws_parent:
                            cur.execute("UPDATE news_articles SET duplicate_of_id = %s WHERE original_url = %s", (aws_parent[0], d.original_url))
                    if d.id % 50 == 0: conn.commit()
                except Exception: pass
            conn.commit()
        
        cur.close(); conn.close()
        complete_job(db, log, ok, err)
    except Exception as e:
        logger.error(f"[INTEGRITY] Fatal: {e}"); complete_job(db, log, 0, 0, str(e))
    finally:
        db.close()
    _banner("FULL INTEGRITY SYNC", False)

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
        res = db.execute(update(NewsArticle).where(NewsArticle.flag!="D", NewsArticle.created_at<datetime.now(timezone.utc)-timedelta(days=30)).values(flag="D", deleted_at=func.now(), updated_at=func.now()))
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

@celery_app.task(name="app.tasks.celery_app.run_master_heartbeat")
def run_master_heartbeat():
    """Coordinated news pipeline heartbeat — runs every 10 mins.
    Minimizes sync overlaps and ensures articles move linearly.
    """
    _banner("MASTER HEARTBEAT")
    t0 = time.time()
    db = get_db()
    
    # 1. Scrape (Every pulse ensures maximum freshness)
    if settings.SCHEDULE_SCRAPE_ENABLED:
        logger.info("[PULSE] Stage 1: Scrape")
        try:
            scrape_all_sources(ignore_window=True) # Run synchronously within heartbeat for order
        except Exception as e:
            logger.warning(f"[PULSE] Scrape failed: {e}")
    
    # 1.5. Self-Healing: Reset failed + stuck "processing" articles
    try:
        from sqlalchemy import update
        # Reset failed/unknown/REWRITE_FAILED articles so Gemini retries them
        res1 = db.execute(update(NewsArticle).where(
            NewsArticle.ai_status.in_(["failed", "unknown"]),  # REWRITE_FAILED retired — local engine handles all failures
            NewsArticle.ai_error_count < 5
        ).values(ai_status="pending", ai_error_count=0, updated_at=func.now()))
        # Reset stuck "processing" articles (stuck > 5 min)
        stuck_cut = datetime.now(timezone.utc) - timedelta(minutes=5)
        res2 = db.execute(update(NewsArticle).where(
            NewsArticle.ai_status == "processing",
            NewsArticle.updated_at < stuck_cut,
        ).values(ai_status="pending", updated_at=func.now()))
        total_reset = (res1.rowcount or 0) + (res2.rowcount or 0)
        if total_reset > 0:
            logger.info(f"[PULSE] Stage 1.5: Self-Healing — reset {total_reset} articles to pending")
        db.commit()
    except Exception as e: logger.warning(f"[PULSE] Self-healing failed: {e}")

    # 2. AI Enrichment (Every pulse)
    if settings.SCHEDULE_AI_ENABLED:
        logger.info("[PULSE] Stage 2: AI")
        process_ai_batch()
    
    # 3. Ranking & Counts (Every pulse)
    if settings.SCHEDULE_RANKING_ENABLED:
        logger.info("[PULSE] Stage 3: Ranking")
        update_top_100_ranking()
    
    if settings.SCHEDULE_CATEGORY_COUNT_ENABLED:
        update_category_counts()

    # 4. Sync to AWS (Every pulse — critical for UI consistency)
    # Also force-sync any articles that are stuck in "processing" state > 30 min
    if settings.SCHEDULE_AWS_SYNC_ENABLED:
        logger.info("[PULSE] Stage 4: AWS Sync")
        try:
            # Reset stuck processing articles before sync
            stuck_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
            stuck = db.execute(update(NewsArticle)
                .where(NewsArticle.ai_status == "processing", NewsArticle.updated_at < stuck_cutoff)
                .values(ai_status="pending", updated_at=func.now()))
            if stuck.rowcount:
                db.commit()
                logger.info(f"[PULSE] Reset {stuck.rowcount} stuck 'processing' articles to pending")
        except Exception as e:
            logger.warning(f"[PULSE] Stuck article reset failed: {e}")
        sync_to_aws()

    # 5. Social Post (Every pulse)
    if settings.SCHEDULE_SOCIAL_ENABLED:
        logger.info("[PULSE] Stage 5: Social")
        post_to_social()

    db.close()
    logger.info(f"[PULSE] Pulse complete in {time.time()-t0:.1f}s")
    _banner("MASTER HEARTBEAT", False)

# Alias for backward compatibility (referenced in scheduler API + __main__)
run_full_pipeline = run_master_heartbeat

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
