
import os
import sys
sys.path.insert(0, os.getcwd())
import psycopg2
from app.config import get_settings
from app.database import SyncSessionLocal
from app.models.models import NewsArticle

settings = get_settings()

def final_aws_sync_cleanup():
    db = SyncSessionLocal()
    local_urls = [a.original_url for a in db.query(NewsArticle).all() if a.original_url]
    db.close()
    
    conn = psycopg2.connect(
        host=settings.AWS_DB_HOST, port=settings.AWS_DB_PORT,
        dbname=settings.AWS_DB_NAME, user=settings.AWS_DB_USER,
        password=settings.AWS_DB_PASSWORD, connect_timeout=10,
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # 1. First, mark anything NOT in local as 'D'
    if local_urls:
        cur.execute("UPDATE news_articles SET flag = 'D' WHERE original_url NOT IN %s AND flag != 'D'", (tuple(local_urls),))
        print(f"Marked {cur.rowcount} AWS articles as 'D' (missing locally)")
    
    # 2. Delete ALL articles with flag='D' in AWS (Full Purge)
    cur.execute("DELETE FROM news_articles WHERE flag = 'D'")
    print(f"Hard deleted {cur.rowcount} articles from AWS (flag='D')")
    
    # 3. Handle NULLs
    cur.execute("DELETE FROM news_articles WHERE original_url IS NULL OR original_url = ''")
    print(f"Deleted {cur.rowcount} corrupted AWS articles")

    cur.close()
    conn.close()

if __name__ == "__main__":
    final_aws_sync_cleanup()
