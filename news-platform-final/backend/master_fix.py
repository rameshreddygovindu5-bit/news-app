import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import update, delete, select, func

from app.database import AsyncSessionLocal, SyncSessionLocal
from app.models.models import NewsArticle, NewsSource, JobExecutionLog, SyncMetadata, Category
from app.tasks.celery_app import update_top_100_ranking, sync_to_aws

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fix_script")

async def run_fixes():
    async with AsyncSessionLocal() as db:
        print("--- Step 1: Clearing Stuck Jobs ---")
        res = await db.execute(
            update(JobExecutionLog)
            .where(JobExecutionLog.status == "RUNNING")
            .values(status="FAILED", error_summary="Manual reset for fixing pipeline")
        )
        await db.commit()
        print(f"Cleared {res.rowcount} stuck jobs.")

        print("--- Step 2: Harmonizing AI Status ---")
        # Ensure all 'A' (processed) articles are marked as 'completed' so they can be ranked
        res = await db.execute(
            update(NewsArticle)
            .where(NewsArticle.flag == "A", NewsArticle.ai_status != "completed")
            .values(ai_status="completed")
        )
        await db.commit()
        print(f"Updated {res.rowcount} articles to 'completed' status.")

        print("--- Step 3: Resetting AWS Sync Metadata ---")
        await db.execute(delete(SyncMetadata).where(SyncMetadata.target == "AWS_PROD"))
        await db.commit()
        print("Reset sync metadata to force full push.")

    print("--- Step 4: Running Ranking Trigger ---")
    # This uses the sync DB internally via get_db() in celery_app.py
    try:
        rank_res = update_top_100_ranking()
        print(f"Ranking Task Result: {rank_res}")
    except Exception as e:
        print(f"Ranking failed: {e}")

    print("--- Step 5: Running AWS Sync ---")
    try:
        sync_res = sync_to_aws()
        print(f"Sync Task Result: {sync_res}")
    except Exception as e:
        print(f"Sync failed: {e}")

    async with AsyncSessionLocal() as db:
        print("--- Final Verification ---")
        y_count = (await db.execute(select(func.count(NewsArticle.id)).filter(NewsArticle.flag == "Y"))).scalar()
        total_local = (await db.execute(select(func.count(NewsArticle.id)))).scalar()
        print(f"Final Local Total: {total_local}")
        print(f"Final Local Top News (Flag Y): {y_count}")

if __name__ == "__main__":
    asyncio.run(run_fixes())
