#!/usr/bin/env python3
"""
Manually trigger AWS sync
"""
import sys
import os
from dotenv import load_dotenv

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def trigger_sync():
    """Trigger immediate AWS sync"""
    print("🚀 Triggering immediate AWS sync...")
    
    try:
        # Import and run the sync function from Celery tasks
        from app.tasks.celery_app import sync_to_aws
        sync_to_aws()
        print("✅ AWS sync triggered successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to trigger AWS sync: {e}")
        return False

if __name__ == "__main__":
    success = trigger_sync()
    sys.exit(0 if success else 1)
