import asyncio
from app.database import AsyncSessionLocal
from app.models.models import SyncMetadata
from sqlalchemy import update, delete
from app.tasks.celery_app import sync_to_aws, update_top_100_ranking

async def force_full_sync():
    async with AsyncSessionLocal() as db:
        print("Resetting AWS Sync Metadata...")
        await db.execute(delete(SyncMetadata).where(SyncMetadata.target == "AWS_PROD"))
        await db.commit()
    
    print("Triggering update_top_100_ranking task...")
    rank_res = update_top_100_ranking()
    print(f"Ranking Task Result: {rank_res}")
    
    print("Triggering sync_to_aws task...")
    result = sync_to_aws()
    print(f"Sync Task Result: {result}")

if __name__ == "__main__":
    asyncio.run(force_full_sync())
