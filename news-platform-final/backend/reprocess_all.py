from sqlalchemy import update, text
from app.database import SyncSessionLocal
from app.models.models import NewsArticle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reprocess")

def reprocess():
    db = SyncSessionLocal()
    try:
        logger.info("Connecting to database...")
        # Reset all articles that are not duplicates
        # We set ai_status to pending and reset the flag to N (not processed for ranking/sync)
        res = db.execute(
            update(NewsArticle)
            .where(NewsArticle.is_duplicate == False)
            .values(
                ai_status="pending",
                flag="N",
                ai_error_count=0
            )
        )
        db.commit()
        logger.info(f"SUCCESS: {res.rowcount} articles marked for AI reprocessing.")
        
        # Also clean up the job logs to start fresh
        db.execute(text("DELETE FROM job_execution_log"))
        db.commit()
        logger.info("Cleared job execution logs.")
        
    except Exception as e:
        logger.error(f"FAILED to reset articles: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reprocess()
