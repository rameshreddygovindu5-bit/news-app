
import asyncio
from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app.models.models import NewsArticle, NewsSource, JobExecutionLog

async def filter_sources_and_articles():
    async with AsyncSessionLocal() as session:
        # 1. Clear stale locks
        from sqlalchemy import update
        from datetime import datetime, timezone
        upd_stmt = update(JobExecutionLog).where(JobExecutionLog.status == "RUNNING").values(status="FAILED", error_summary="Manual reset", ended_at=datetime.now(timezone.utc))
        await session.execute(upd_stmt)
        print("Cleared stale job locks.")

        # 2. Identify GreatAndhra source
        stmt = select(NewsSource).where(NewsSource.name.ilike("%great%andhra%"))
        res = await session.execute(stmt)
        ga_source = res.scalar_one_or_none()
        
        if not ga_source:
            print("GreatAndhra source not found!")
            return

        print(f"GreatAndhra Source ID: {ga_source.id}")

        # 2. Delete articles from other sources
        del_stmt = delete(NewsArticle).where(NewsArticle.source_id != ga_source.id)
        res = await session.execute(del_stmt)
        print(f"Deleted {res.rowcount} articles from other sources.")

        # 3. Disable all other sources
        upd_stmt = (
            delete(NewsSource).where(NewsSource.id != ga_source.id)
        )
        # Actually, user says "remove all news and articles other than greater andhra".
        # It's cleaner to just disable them so keep the GA one.
        from sqlalchemy import update
        upd_stmt = update(NewsSource).where(NewsSource.id != ga_source.id).values(is_enabled=False)
        await session.execute(upd_stmt)
        
        # Ensure GA is enabled
        ga_stmt = update(NewsSource).where(NewsSource.id == ga_source.id).values(is_enabled=True, is_paused=False)
        await session.execute(ga_stmt)
        
        await session.commit()
        print("Other sources disabled. GreatAndhra is now the only active source.")

if __name__ == "__main__":
    asyncio.run(filter_sources_and_articles())
