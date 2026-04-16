
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.models import JobExecutionLog

async def check_logs():
    async with AsyncSessionLocal() as session:
        stmt = select(JobExecutionLog).order_by(JobExecutionLog.started_at.desc()).limit(5)
        res = await session.execute(stmt)
        logs = res.scalars().all()
        for log in logs:
            print(f"Job: {log.job_name}, Status: {log.status}, OK: {log.rows_ok}, ERR: {log.rows_err}, Error: {log.error_summary}")

if __name__ == "__main__":
    asyncio.run(check_logs())
