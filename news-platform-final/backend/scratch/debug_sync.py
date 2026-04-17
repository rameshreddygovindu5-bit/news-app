
import os
import sys
sys.path.insert(0, os.getcwd())
import psycopg2
from app.database import SyncSessionLocal
from app.models.models import NewsArticle
from app.config import get_settings

settings = get_settings()

def debug_sync():
    db = SyncSessionLocal()
    local_urls = set(a.original_url for a in db.query(NewsArticle).all())
    db.close()

    conn = psycopg2.connect(
        host=settings.AWS_DB_HOST, port=settings.AWS_DB_PORT,
        dbname=settings.AWS_DB_NAME, user=settings.AWS_DB_USER,
        password=settings.AWS_DB_PASSWORD, connect_timeout=10,
    )
    cur = conn.cursor()
    cur.execute("SELECT original_url, flag FROM news_articles WHERE flag IN ('A', 'Y')")
    aws_published = cur.fetchall()
    
    mismatch = []
    for url, flag in aws_published:
        if url not in local_urls:
            mismatch.append(url)
    
    print(f"AWS published articles NOT in local: {len(mismatch)}")
    for u in mismatch[:5]:
        print(f" - {u}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    debug_sync()
