
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load .env from the backend directory
load_dotenv('news-platform-final/backend/.env')

def full_check_aws():
    host = os.getenv('AWS_DB_HOST')
    port = os.getenv('AWS_DB_PORT', 5432)
    dbname = os.getenv('AWS_DB_NAME')
    user = os.getenv('AWS_DB_USER')
    password = os.getenv('AWS_DB_PASSWORD')

    print(f"--- AWS DB Audit: {host} ---")
    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname=dbname, user=user, password=password, connect_timeout=10
        )
        cur = conn.cursor()
        
        # 1. Articles
        cur.execute("SELECT count(*) FROM news_articles")
        print(f"Articles: {cur.fetchone()[0]}")
        
        cur.execute("SELECT flag, count(*) FROM news_articles GROUP BY flag")
        print("Flags:", cur.fetchall())
        
        # 2. Categories
        cur.execute("SELECT count(*) FROM categories WHERE is_active = TRUE")
        print(f"Active Categories: {cur.fetchone()[0]}")
        
        # 3. Sources
        cur.execute("SELECT count(*) FROM news_sources WHERE is_enabled = TRUE")
        print(f"Enabled Sources: {cur.fetchone()[0]}")
        
        # 4. Wishes
        try:
            cur.execute("SELECT count(*) FROM wishes WHERE is_active = TRUE")
            print(f"Active Wishes: {cur.fetchone()[0]}")
        except:
            print("Wishes table missing or error")
            conn.rollback() # Reset transaction after error
        
        # 5. Polls
        try:
            cur.execute("SELECT count(*) FROM polls WHERE is_active = TRUE")
            print(f"Active Polls: {cur.fetchone()[0]}")
        except:
            print("Polls table missing or error")
            conn.rollback()

        # 6. Check for telugu content
        cur.execute("SELECT count(*) FROM news_articles WHERE telugu_title IS NOT NULL AND telugu_title != ''")
        print(f"Articles with Telugu: {cur.fetchone()[0]}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    full_check_aws()
