
import psycopg2
from app.config import get_settings
from app.database import SyncSessionLocal
from app.models.models import NewsArticle, SyncMetadata
from app.tasks.celery_app import full_integrity_sync
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nuclear_sync")

def main():
    settings = get_settings()
    
    if not (settings.AWS_DB_HOST and settings.AWS_DB_USER and settings.AWS_DB_PASSWORD):
        print("AWS credentials not configured in .env")
        return

    print(f"Connecting to AWS Database: {settings.AWS_DB_HOST}...")
    try:
        conn = psycopg2.connect(
            host=settings.AWS_DB_HOST,
            port=settings.AWS_DB_PORT,
            dbname=settings.AWS_DB_NAME,
            user=settings.AWS_DB_USER,
            password=settings.AWS_DB_PASSWORD,
            connect_timeout=15
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Nuclear Option: Removing all news articles from AWS...")
        # Use TRUNCATE with CASCADE to handle self-referencing duplicate_of_id
        cur.execute("TRUNCATE news_articles RESTART IDENTITY CASCADE;")
        print("AWS news_articles truncated successfully.")
        
        cur.close()
        conn.close()
        
        print("Resetting local sync metadata...")
        db = SyncSessionLocal()
        try:
            db.query(SyncMetadata).filter(SyncMetadata.target == "AWS_PROD").delete()
            db.commit()
        finally:
            db.close()
            
        print("Starting Full Integrity Sync (Pushing all local news)...")
        full_integrity_sync()
        
        print("\nNuclear Sync Complete! All local news pushed to a clean AWS database.")
        
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    main()
