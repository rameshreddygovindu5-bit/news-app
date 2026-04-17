
import os
import sys
sys.path.insert(0, os.getcwd())
import psycopg2
from app.database import SyncSessionLocal
from app.models.models import NewsArticle
from app.config import get_settings

settings = get_settings()

def get_local_stats():
    db = SyncSessionLocal()
    total = db.query(NewsArticle).count()
    published = db.query(NewsArticle).filter(NewsArticle.flag.in_(['A', 'Y'])).count()
    db.close()
    return total, published

def get_aws_stats():
    try:
        conn = psycopg2.connect(
            host=settings.AWS_DB_HOST, port=settings.AWS_DB_PORT,
            dbname=settings.AWS_DB_NAME, user=settings.AWS_DB_USER,
            password=settings.AWS_DB_PASSWORD, connect_timeout=10,
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM news_articles")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM news_articles WHERE flag IN ('A', 'Y')")
        published = cur.fetchone()[0]
        cur.close()
        conn.close()
        return total, published
    except Exception as e:
        return f"Error: {e}", 0

if __name__ == "__main__":
    lt, lp = get_local_stats()
    at, ap = get_aws_stats()
    print(f"Local Total: {lt}, Published: {lp}")
    print(f"AWS Total:   {at}, Published: {ap}")
