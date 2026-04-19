import logging
from app.tasks.celery_app import worker_scrape_source, process_ai_batch, sync_to_aws

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bootstrap")

def run_bootstrap():
    new_source_ids = [13, 14, 15, 16, 17]
    
    # 1. Scrape
    for sid in new_source_ids:
        logger.info(f"--- Scraping Source {sid} ---")
        try:
            worker_scrape_source(sid, "manual_bootstrap")
        except Exception as e:
            logger.error(f"Error scraping {sid}: {e}")

    # 2. AI Enrichment
    logger.info("--- Running AI Enrichment ---")
    try:
        process_ai_batch()
    except Exception as e:
        logger.error(f"Error in AI processing: {e}")

    # 3. AWS Sync
    logger.info("--- Syncing to AWS ---")
    try:
        sync_to_aws()
    except Exception as e:
        logger.error(f"Error in AWS sync: {e}")

    logger.info("--- Bootstrap Complete ---")

if __name__ == "__main__":
    run_bootstrap()
