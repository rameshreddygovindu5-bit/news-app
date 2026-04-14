
import asyncio
from app.database import AsyncSessionLocal
from app.models.models import AdminUser
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(AdminUser))
        users = res.scalars().all()
        print(f"Admin Users found: {[u.username for u in users]}")

if __name__ == "__main__":
    asyncio.run(check())
