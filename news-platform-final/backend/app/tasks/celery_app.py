"""
Celery Task Pipeline v7.1 — High-Performance Edition
===================================================
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
    PostErrorLog, SyncMetadata, SourceErrorLog, Wish, PollOption, Poll
)
from app.scrapers.base_scraper import ScraperFactory
from app.services.ai_service import ai_service
from app.services.social_service import social_service

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery("news_aggregator", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_serializer="json", accept_content=["json"], result_serializer="json",
    timezone="UTC", enable_utc=True, task_track_started=True,
    task_acks_late=True, worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

def get_db() -> Session: return SyncSessionLocal()

def log_job(db, job_name, triggered_by="cron"):
    run_id = str(uuid.uuid4())
    log_entry = JobExecutionLog(job_name=job_name, run_id=run_id, started_at=datetime.now(timezone.utc), status="RUNNING", triggered_by=triggered_by)
    db.add(log_entry); db.commit(); db.refresh(log_entry)
    return log_entry

def complete_job(db, log, ok, err, error_summary=None):
    if not log: return
    log.status = "DONE" if err==0 else "PARTIAL"
    log.rows_ok=ok; log.rows_err=err; log.ended_at=datetime.now(timezone.utc)
    log.duration_s=(log.ended_at-log.started_at.replace(tzinfo=timezone.utc)).total_seconds()
    db.commit()

def _banner(label, start=True):
    v = "STARTING" if start else "DONE"
    logger.info(f"\n{'━'*60}\n  {v}: {label}\n{'━'*60}")

@celery_app.task(name="app.tasks.celery_app.scrape_all_sources")
def scrape_all_sources(ignore_window=False):
    _banner("SCRAPE")
    db = get_db(); log = log_job(db, "scrape_sources")
    if not log: return
    try:
        sources = db.query(NewsSource).filter(NewsSource.is_enabled==True).all()
        ok = err = 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(worker_scrape_source, s.id, log.run_id): s for s in sources}
            for f in as_completed(futures):
                r = f.result(); ok+=r["inserted"]; err+=r["errors"]
        complete_job(db, log, ok, err)
    finally: db.close()

def worker_scrape_source(source_id, run_id):
    db = SyncSessionLocal(); stats = {"inserted": 0, "errors": 0}
    try:
        src = db.query(NewsSource).get(source_id)
        scraper = ScraperFactory.create({"name":src.name,"url":src.url,"scraper_type":src.scraper_type,"language":src.language,"scraper_config":src.scraper_config or {}})
        loop = asyncio.new_event_loop()
        articles = loop.run_until_complete(scraper.scrape()); loop.close()
        for a in articles:
            ch = hashlib.sha256(f"{source_id}{a.title.lower()}".encode()).hexdigest()
            if db.query(NewsArticle.id).filter(NewsArticle.content_hash==ch).first(): continue
            slug = f"{re.sub(r'[^\\w\\s-]','',a.title.lower())[:80].replace(' ','-')}-{hashlib.md5(a.url.encode()).hexdigest()[:4]}"
            db.add(NewsArticle(source_id=source_id, original_title=a.title, original_content=a.content, original_url=a.url, original_language=src.language, content_hash=ch, flag="N", ai_status="pending", category="Home", slug=slug, image_url=a.image_url))
            stats["inserted"] += 1
        src.last_scraped_at = datetime.now(timezone.utc); db.commit()
    except Exception: stats["errors"] = 1
    finally: db.close()
    return stats

@celery_app.task(name="app.tasks.celery_app.process_ai_batch")
def process_ai_batch():
    _banner("AI")
    db = get_db(); log = log_job(db, "ai_enrichment")
    if not log: return
    try:
        pending = db.query(NewsArticle).filter(NewsArticle.ai_status=="pending", NewsArticle.is_duplicate==False).limit(settings.AI_BATCH_SIZE).all()
        ok = err = 0
        for art in pending:
            res = ai_service.process_article(art.original_title, art.original_content or "")
            art.rephrased_title = res["rephrased_title"]
            art.rephrased_content = res["rephrased_content"]
            art.telugu_title = res["telugu_title"]
            art.telugu_content = res["telugu_content"]
            art.category = res["category"]
            art.ai_status = res["ai_status_code"]
            art.flag = "A"
            art.processed_at = datetime.now(timezone.utc)
            ok += 1
        db.commit(); complete_job(db, log, ok, err)
    finally: db.close()

@celery_app.task(name="app.tasks.celery_app.update_top_100_ranking")
def update_top_100_ranking():
    _banner("RANK")
    db = get_db(); log = log_job(db, "ranking")
    if not log: return
    try:
        db.execute(update(NewsArticle).where(NewsArticle.flag=="Y").values(flag="A", updated_at=func.now()))
        top = db.query(NewsArticle).filter(NewsArticle.flag=="A").order_by(desc(NewsArticle.created_at)).limit(200).all()
        for a in top: a.flag = "Y"
        db.commit(); complete_job(db, log, len(top), 0)
    finally: db.close()

@celery_app.task(name="app.tasks.celery_app.sync_to_aws")
def sync_to_aws():
    _banner("AWS SYNC")
    db = get_db(); log = log_job(db, "aws_sync")
    if not log: return
    try:
        conn = psycopg2.connect(host=settings.AWS_DB_HOST, port=settings.AWS_DB_PORT, dbname=settings.AWS_DB_NAME, user=settings.AWS_DB_USER, password=settings.AWS_DB_PASSWORD, connect_timeout=10)
        cur = conn.cursor()
        
        # Optimized Bulk Sync: Categories
        cats = db.query(Category).all()
        if cats: execute_values(cur, "INSERT INTO categories (name,slug,description,is_active,article_count) VALUES %s ON CONFLICT (name) DO UPDATE SET is_active=EXCLUDED.is_active", [(c.name, c.slug, c.description, c.is_active, c.article_count) for c in cats])
        
        # Optimized Bulk Sync: Sources
        srcs = db.query(NewsSource).all()
        if srcs: execute_values(cur, "INSERT INTO news_sources (id,name,url,scraper_type,language,is_enabled) VALUES %s ON CONFLICT (id) DO UPDATE SET is_enabled=EXCLUDED.is_enabled", [(s.id, s.name, s.url, s.scraper_type, s.language, s.is_enabled) for s in srcs])
        
        # Optimized Bulk Sync: Articles (Delta)
        meta = db.query(SyncMetadata).filter(SyncMetadata.target=="AWS_PROD").first()
        if not meta: meta = SyncMetadata(target="AWS_PROD", last_sync_at=datetime.now(timezone.utc)-timedelta(days=1)); db.add(meta); db.commit()
        
        recs = db.query(NewsArticle).filter(NewsArticle.updated_at > meta.last_sync_at - timedelta(minutes=5)).all()
        if recs:
            SQL = "INSERT INTO news_articles (source_id,original_title,original_content,original_url,original_language,rephrased_title,rephrased_content,telugu_title,telugu_content,category,slug,flag,updated_at) VALUES %s ON CONFLICT (original_url) DO UPDATE SET flag=EXCLUDED.flag, rephrased_title=EXCLUDED.rephrased_title, telugu_title=EXCLUDED.telugu_title, updated_at=EXCLUDED.updated_at"
            data = [(r.source_id, r.original_title, r.original_content, r.original_url, r.original_language, r.rephrased_title, r.rephrased_content, r.telugu_title, r.telugu_content, r.category, r.slug, r.flag, r.updated_at) for r in recs]
            execute_values(cur, SQL, data)
            meta.last_sync_at = datetime.now(timezone.utc)
        
        conn.commit(); cur.close(); conn.close()
        complete_job(db, log, len(recs), 0)
    except Exception as e: logger.error(f"Sync error: {e}")
    finally: db.close()

@celery_app.task(name="app.tasks.celery_app.run_master_heartbeat")
def run_master_heartbeat():
    _banner("HEARTBEAT")
    scrape_all_sources()
    process_ai_batch()
    update_top_100_ranking()
    sync_to_aws()
    _banner("HEARTBEAT", False)

if __name__ == "__main__":
    run_master_heartbeat()
