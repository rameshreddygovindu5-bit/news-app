from app.database import SyncSessionLocal
from app.models.models import JobExecutionLog

def reset_running_jobs():
    db = SyncSessionLocal()
    try:
        running = db.query(JobExecutionLog).filter(JobExecutionLog.status == "RUNNING").all()
        for job in running:
            job.status = "INTERRUPTED"
            print(f"Reset job: {job.job_name} ({job.started_at})")
        db.commit()
        print(f"Total jobs reset: {len(running)}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_running_jobs()
