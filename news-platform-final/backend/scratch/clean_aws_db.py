
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def cleanup_aws_db():
    host = os.getenv("AWS_DB_HOST")
    port = os.getenv("AWS_DB_PORT", 5432)
    dbname = os.getenv("AWS_DB_NAME")
    user = os.getenv("AWS_DB_USER")
    password = os.getenv("AWS_DB_PASSWORD")

    print(f"Connecting to AWS DB: {host}...")
    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname=dbname,
            user=user, password=password, connect_timeout=15
        )
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Find GreatAndhra
        cur.execute("SELECT id FROM news_sources WHERE name ILIKE '%Great%Andhra%'")
        row = cur.fetchone()
        if not row:
            print("GreatAndhra source not found on AWS!")
            return
        ga_id = row[0]
        print(f"GreatAndhra ID on AWS: {ga_id}")

        # 2. Clear foreign key references to avoid constraint violations
        cur.execute("UPDATE news_articles SET duplicate_of_id = NULL")
        
        # 3. Delete articles from other sources
        cur.execute("DELETE FROM news_articles WHERE source_id != %s", (ga_id,))
        print(f"Deleted {cur.rowcount} articles from other sources on AWS.")

        # 4. Disable other sources
        cur.execute("UPDATE news_sources SET is_enabled = FALSE WHERE id != %s", (ga_id,))
        print(f"Disabled other sources on AWS.")
        
        # 4. Enable GreatAndhra
        cur.execute("UPDATE news_sources SET is_enabled = TRUE, is_paused = FALSE WHERE id = %s", (ga_id,))

        cur.close()
        conn.close()
        print("AWS Database cleanup complete.")

    except Exception as e:
        print(f"Error connecting to AWS DB: {e}")

if __name__ == "__main__":
    cleanup_aws_db()
