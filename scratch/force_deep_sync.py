
import asyncio
from app.tasks.celery_app import full_integrity_sync

async def run_it():
    print("Starting full integrity sync to AWS...")
    # Since full_integrity_sync is a Celery task, we call it directly here
    full_integrity_sync()
    print("Done!")

if __name__ == "__main__":
    import os
    import sys
    # Add project root to path
    sys.path.append(os.path.join(os.getcwd(), 'news-platform-final', 'backend'))
    
    # We need to run it in a sync context because full_integrity_sync is a sync function inside the module
    full_integrity_sync()
