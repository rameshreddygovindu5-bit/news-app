import psycopg2
import sqlite3
import os
import hashlib
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv()

def sync_articles_fixed():
    print("Syncing Articles to AWS (with content_hash)...")
    local_conn = sqlite3.connect('newsagg.db')
    local_cur = local_conn.cursor()
    
    try:
        aws_conn = psycopg2.connect(
            host=os.getenv("AWS_DB_HOST"),
            port=os.getenv("AWS_DB_PORT"),
            dbname=os.getenv("AWS_DB_NAME"),
            user=os.getenv("AWS_DB_USER"),
            password=os.getenv("AWS_DB_PASSWORD"),
            connect_timeout=20
        )
        aws_cur = aws_conn.cursor()
        
        # First, ensure all articles have content_hash
        local_cur.execute("SELECT id, original_title, original_content FROM news_articles WHERE content_hash IS NULL OR content_hash = ''")
        articles_without_hash = local_cur.fetchall()
        if articles_without_hash:
            print(f"Generating content_hash for {len(articles_without_hash)} articles...")
            for art_id, title, content in articles_without_hash:
                hash_input = f"{title or ''}{content or ''}"
                content_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
                local_cur.execute("UPDATE news_articles SET content_hash = ? WHERE id = ?", (content_hash, art_id))
            local_conn.commit()
        
        local_cur.execute("SELECT source_id, original_title, original_content, original_url, original_language, rephrased_title, rephrased_content, telugu_title, telugu_content, category, slug, flag, updated_at, content_hash FROM news_articles")
        recs = local_cur.fetchall()
        if recs:
            print(f"Pushing {len(recs)} articles...")
            SQL = ("INSERT INTO news_articles (source_id, original_title, original_content, original_url, original_language, rephrased_title, rephrased_content, telugu_title, telugu_content, category, slug, flag, updated_at, content_hash) "
                   "VALUES %s ON CONFLICT (original_url) DO UPDATE SET flag=EXCLUDED.flag, rephrased_title=EXCLUDED.rephrased_title, telugu_title=EXCLUDED.telugu_title, updated_at=EXCLUDED.updated_at, content_hash=EXCLUDED.content_hash")
            execute_values(aws_cur, SQL, recs)
            aws_conn.commit()
            print("Done.")
            
        aws_cur.close()
        aws_conn.close()
    except Exception as e:
        with open("sync_error.txt", "w", encoding="utf-8") as f:
            f.write(str(e))
    finally:
        local_conn.close()

if __name__ == "__main__":
    sync_articles_fixed()
