
import asyncio
from app.database import AsyncSessionLocal
from app.models.models import NewsSource
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(NewsSource))
        sources = res.scalars().all()
        print(f"Sources found: {[s.name for s in sources]}")

if __name__ == "__main__":
    asyncio.run(check())
