import logging
import asyncio
from app.database import SyncSessionLocal
from app.models.models import NewsArticle, NewsSource, SyncMetadata, Category, JobExecutionLog
from app.tasks.celery_app import worker_scrape_source, process_ai_batch, sync_to_aws, update_top_100_ranking
from datetime import datetime, timezone, timedelta
from sqlalchemy import update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("final_boot")

def final_sync_workflow():
    db = SyncSessionLocal()
    try:
        # 1. Fix Categories & Flags for Google News Sources
        # Sources 13=World, 14=U.S., 15=Business, 16=Tech, 17=India
        mapping = {13: "World", 14: "U.S.", 15: "Business", 16: "Tech", 17: "India"}
        for sid, cat in mapping.items():
            db.execute(update(NewsArticle).where(NewsArticle.source_id == sid).values(category=cat, flag="Y"))
        db.commit()
        logger.info("Fixed categories and set flag='Y' for sources 13-17.")

        # 2. Reset Sync Metadata to force full re-sync
        meta = db.query(SyncMetadata).filter(SyncMetadata.target == "AWS_PROD").first()
        if meta:
            meta.last_sync_at = datetime.now(timezone.utc) - timedelta(days=30)
            db.commit()
            logger.info("Reset AWS Sync metadata to force full update.")

        # 3. Trigger Scrape for these sources (id 13-17)
        for sid in mapping.keys():
            logger.info(f"Scraping source {sid}...")
            worker_scrape_source(sid, "manual_final_bootstrap")

        # 4. Run AI Enrichment (Process any 'pending' or 'failed' articles)
        logger.info("Running AI Enrichment...")
        process_ai_batch()

        # 5. Run Ranking (Ensure Top News is updated locally)
        logger.info("Running Ranking...")
        update_top_100_ranking()

        # 6. Final Sync to AWS
        logger.info("Triggering Final Sync to AWS...")
        sync_to_aws()

        logger.info("Workflow execution finished.")
    finally:
        db.close()

if __name__ == "__main__":
    final_sync_workflow()
