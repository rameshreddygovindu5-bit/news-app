
import os
import sys
sys.path.insert(0, os.getcwd())
import psycopg2
from app.config import get_settings

settings = get_settings()

def cleanup_aws():
    conn = psycopg2.connect(
        host=settings.AWS_DB_HOST, port=settings.AWS_DB_PORT,
        dbname=settings.AWS_DB_NAME, user=settings.AWS_DB_USER,
        password=settings.AWS_DB_PASSWORD, connect_timeout=10,
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # 1. Delete articles with null or empty URLs
    cur.execute("DELETE FROM news_articles WHERE original_url IS NULL OR original_url = ''")
    print(f"Deleted {cur.rowcount} articles with null/empty URLs")
    
    # 2. Delete articles with 'None' string as URL (just in case)
    cur.execute("DELETE FROM news_articles WHERE original_url = 'None'")
    print(f"Deleted {cur.rowcount} articles with 'None' URLs")
    
    # 3. Mark anything not in local as 'D' (re-run pruning to be sure)
    from app.database import SyncSessionLocal
    from app.models.models import NewsArticle
    db = SyncSessionLocal()
    local_urls = [a.original_url for a in db.query(NewsArticle).all() if a.original_url]
    db.close()
    
    # 4. Hard delete everything with flag='D' in AWS for a clean match
    cur.execute("DELETE FROM news_articles WHERE flag = 'D'")
    print(f"Hard deleted {cur.rowcount} AWS articles (flag='D')")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    cleanup_aws()
