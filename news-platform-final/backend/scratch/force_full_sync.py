
import os
import sys
import json
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.getcwd())
import psycopg2
from app.database import SyncSessionLocal
from app.models.models import NewsArticle, SyncMetadata, Category, NewsSource
from app.config import get_settings

settings = get_settings()

def force_full_sync():
    print("Starting Force Full Sync...")
    db = SyncSessionLocal()
    
    # 1. Get all local URLs
    local_articles = db.query(NewsArticle).all()
    local_urls = [a.original_url for a in local_articles]
    print(f"Local articles: {len(local_urls)}")

    # 2. Connect to AWS
    try:
        conn = psycopg2.connect(
            host=settings.AWS_DB_HOST, port=settings.AWS_DB_PORT,
            dbname=settings.AWS_DB_NAME, user=settings.AWS_DB_USER,
            password=settings.AWS_DB_PASSWORD, connect_timeout=15,
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # 3. Mark articles in AWS that are NOT in local as 'D'
        print("Pruning AWS articles...")
        # We'll do this by taking chunks of URLs to avoid huge IN clauses
        # Or better, just mark everything as 'D' first? 
        # Actually, let's just mark everything that is NOT in the local_urls list.
        # But 300 URLs is small enough for a single query.
        
        if local_urls:
            # Mark all as 'D' except those in local_urls
            cur.execute("UPDATE news_articles SET flag = 'D' WHERE original_url NOT IN %s AND flag != 'D'", (tuple(local_urls),))
            print(f"AWS pruning done: {cur.rowcount} articles marked as 'D'")
        else:
            cur.execute("UPDATE news_articles SET flag = 'D' WHERE flag != 'D'")
            print("All AWS articles marked as 'D' (local was empty)")

        # 4. Now run the normal sync for ALL local articles (ignore metadata)
        print("Syncing all local articles to AWS...")
        ok = err = 0
        SQL = """INSERT INTO news_articles (source_id,original_title,original_content,original_url,original_language,published_at,rephrased_title,rephrased_content,category,slug,tags,flag,image_url,author,content_hash,is_duplicate,duplicate_of_id,rank_score,telugu_title,telugu_content,created_at,updated_at)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                 ON CONFLICT (original_url) DO UPDATE SET
                   original_title=EXCLUDED.original_title, original_content=EXCLUDED.original_content,
                   rephrased_title=EXCLUDED.rephrased_title, rephrased_content=EXCLUDED.rephrased_content,
                   telugu_title=EXCLUDED.telugu_title, telugu_content=EXCLUDED.telugu_content,
                   category=EXCLUDED.category, slug=EXCLUDED.slug, tags=EXCLUDED.tags, flag=EXCLUDED.flag,
                   image_url=EXCLUDED.image_url, author=EXCLUDED.author, rank_score=EXCLUDED.rank_score,
                   updated_at=EXCLUDED.updated_at"""
        
        for art in local_articles:
            try:
                tags = art.tags
                if tags and isinstance(tags, str):
                    try: tags = json.loads(tags)
                    except: tags = []
                elif not tags:
                    tags = []
                
                cur.execute(SQL, (
                    art.source_id, art.original_title, art.original_content, art.original_url,
                    art.original_language, art.published_at, art.rephrased_title, art.rephrased_content,
                    art.category, art.slug, tags, art.flag, art.image_url, art.author,
                    art.content_hash, bool(art.is_duplicate), art.duplicate_of_id, art.rank_score,
                    getattr(art,'telugu_title',''), getattr(art,'telugu_content',''),
                    art.created_at, art.updated_at,
                ))
                ok += 1
            except Exception as e:
                print(f"Error syncing {art.id}: {e}")
                err += 1

        # 5. Update metadata
        meta = db.query(SyncMetadata).filter(SyncMetadata.target=="AWS_PROD").first()
        if meta:
            meta.last_sync_at = datetime.now(timezone.utc)
            meta.last_rows_ok = ok
            meta.last_rows_err = err
            db.commit()

        print(f"Full Sync Done. Synced: {ok}, Failed: {err}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    force_full_sync()
