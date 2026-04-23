import psycopg2
import sqlite3
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from psycopg2.extras import execute_values

load_dotenv()

def nuclear_sync():
    print("Starting Nuclear Sync (Force Push ALL articles to AWS)...")
    
    # Local SQLite
    local_conn = sqlite3.connect('newsagg.db')
    local_cur = local_conn.cursor()
    
    # AWS PostgreSQL
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
    except Exception as e:
        print(f"Error connecting to AWS: {e}")
        return

    try:
        # Sync Categories
        local_cur.execute("SELECT name, slug, description, is_active, article_count FROM categories")
        cats = local_cur.fetchall()
        if cats:
            execute_values(aws_cur, 
                "INSERT INTO categories (name, slug, description, is_active, article_count) VALUES %s "
                "ON CONFLICT (name) DO UPDATE SET is_active=EXCLUDED.is_active, article_count=EXCLUDED.article_count", 
                [(c[0], c[1], c[2], bool(c[3]), c[4]) for c in cats])
            print(f"Synced {len(cats)} categories.")

        # Sync Sources
        local_cur.execute("SELECT id, name, url, scraper_type, language, is_enabled FROM news_sources")
        srcs = local_cur.fetchall()
        if srcs:
            execute_values(aws_cur, 
                "INSERT INTO news_sources (id, name, url, scraper_type, language, is_enabled) VALUES %s "
                "ON CONFLICT (id) DO UPDATE SET is_enabled=EXCLUDED.is_enabled, name=EXCLUDED.name", 
                [(s[0], s[1], s[2], s[3], s[4], bool(s[5])) for s in srcs])
            print(f"Synced {len(srcs)} sources.")

        # Sync ALL Articles (Nuclear)
        local_cur.execute("SELECT source_id, original_title, original_content, original_url, original_language, rephrased_title, rephrased_content, telugu_title, telugu_content, category, slug, flag, updated_at FROM news_articles")
        recs = local_cur.fetchall()
        if recs:
            print(f"Pushing {len(recs)} articles to AWS...")
            SQL = ("INSERT INTO news_articles (source_id, original_title, original_content, original_url, original_language, rephrased_title, rephrased_content, telugu_title, telugu_content, category, slug, flag, updated_at) "
                   "VALUES %s ON CONFLICT (original_url) DO UPDATE SET flag=EXCLUDED.flag, rephrased_title=EXCLUDED.rephrased_title, telugu_title=EXCLUDED.telugu_title, updated_at=EXCLUDED.updated_at")
            execute_values(aws_cur, SQL, recs)
            print("Nuclear push complete.")

        aws_conn.commit()
    except Exception as e:
        print(f"Sync error: {e}")
        aws_conn.rollback()
    finally:
        aws_cur.close()
        aws_conn.close()
        local_conn.close()

if __name__ == "__main__":
    nuclear_sync()
