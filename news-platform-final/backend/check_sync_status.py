
import psycopg2
from app.config import get_settings
from app.database import SyncSessionLocal
from app.models.models import NewsArticle
from sqlalchemy import select, func

def main():
    settings = get_settings()
    
    # Check Local
    db = SyncSessionLocal()
    local_count = db.execute(select(func.count(NewsArticle.id)).where(NewsArticle.flag != 'D')).scalar()
    local_telugu = db.execute(select(func.count(NewsArticle.id)).where(NewsArticle.flag != 'D', NewsArticle.telugu_title != '')).scalar()
    local_top = db.execute(select(func.count(NewsArticle.id)).where(NewsArticle.flag == 'Y')).scalar()
    db.close()
    
    print(f"LOCAL DATA:")
    print(f"  Total Articles (Non-D): {local_count}")
    print(f"  Articles with Telugu Content: {local_telugu}")
    print(f"  Top News (Y): {local_top}")
    
    # Check AWS
    if not (settings.AWS_DB_HOST and settings.AWS_DB_USER and settings.AWS_DB_PASSWORD):
        print("AWS credentials not configured.")
        return

    try:
        conn = psycopg2.connect(
            host=settings.AWS_DB_HOST,
            port=settings.AWS_DB_PORT,
            dbname=settings.AWS_DB_NAME,
            user=settings.AWS_DB_USER,
            password=settings.AWS_DB_PASSWORD,
            connect_timeout=15
        )
        cur = conn.cursor()
        
        cur.execute("SELECT count(*) FROM news_articles WHERE flag != 'D'")
        aws_count = cur.fetchone()[0]
        
        cur.execute("SELECT count(*) FROM news_articles WHERE flag != 'D' AND telugu_title IS NOT NULL AND telugu_title != ''")
        aws_telugu = cur.fetchone()[0]
        
        cur.execute("SELECT count(*) FROM news_articles WHERE flag = 'Y'")
        aws_top = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        print(f"\nAWS DATA:")
        print(f"  Total Articles (Non-D): {aws_count}")
        print(f"  Articles with Telugu Content: {aws_telugu}")
        print(f"  Top News (Y): {aws_top}")
        
    except Exception as e:
        print(f"AWS Error: {e}")

if __name__ == "__main__":
    main()
