import logging
import sys
import os

# Add the current directory to sys.path to import app
sys.path.append(os.getcwd())

from app.tasks.celery_app import process_ai_batch
from app.database import SyncSessionLocal
from app.models.models import NewsArticle
from sqlalchemy import select, func

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trigger_ai")

def trigger():
    db = SyncSessionLocal()
    try:
        # Count pending articles
        pending_count = db.execute(
            select(func.count(NewsArticle.id))
            .where(NewsArticle.ai_status.in_(["pending", "unknown"]), NewsArticle.is_duplicate == False)
        ).scalar() or 0
        
        logger.info(f"Found {pending_count} pending articles.")
        
        if pending_count == 0:
            logger.info("No articles to process.")
            return

        # Process in batches
        batches = (pending_count // 50) + 1
        for i in range(batches):
            logger.info(f"Processing batch {i+1}/{batches}...")
            process_ai_batch()
            
        logger.info("Reprocessing complete.")
    except Exception as e:
        logger.error(f"Trigger failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    trigger()
