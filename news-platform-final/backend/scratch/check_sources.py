
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.models import NewsSource

async def check_sources():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(NewsSource))
        sources = result.scalars().all()
        for s in sources:
            print(f"ID: {s.id}, Name: {s.name}, ScraperType: {s.scraper_type}")

if __name__ == "__main__":
    asyncio.run(check_sources())
