
import psycopg2
import os
from dotenv import load_dotenv

# Load .env from the backend directory
load_dotenv('news-platform-final/backend/.env')

def check_aws():
    host = os.getenv('AWS_DB_HOST')
    port = os.getenv('AWS_DB_PORT', 5432)
    dbname = os.getenv('AWS_DB_NAME')
    user = os.getenv('AWS_DB_USER')
    password = os.getenv('AWS_DB_PASSWORD')

    print(f"Connecting to AWS DB: {host} as {user}...")
    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname=dbname, user=user, password=password, connect_timeout=10
        )
        cur = conn.cursor()
        
        # 1. Check articles
        cur.execute("SELECT count(*) FROM news_articles")
        count = cur.fetchone()[0]
        print(f"SUCCESS! Total articles in AWS: {count}")
        
        # 2. Check flags
        cur.execute("SELECT flag, count(*) FROM news_articles GROUP BY flag")
        results = cur.fetchall()
        print("Article status flags in AWS:")
        for r in results:
            print(f"  {r[0]}: {r[1]}")
            
        # 3. Check for recent syncs
        cur.execute("SELECT MAX(updated_at) FROM news_articles")
        last_update = cur.fetchone()[0]
        print(f"Last updated article in AWS: {last_update}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"FAILED to connect to AWS: {e}")

if __name__ == "__main__":
    check_aws()
