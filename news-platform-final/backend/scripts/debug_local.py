
import sqlite3
import os

def check_local():
    db_path = 'news-platform-final/backend/newsagg.db'
    print(f"Connecting to Local SQLite: {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 1. Check articles
        cur.execute("SELECT count(*) FROM news_articles")
        count = cur.fetchone()[0]
        print(f"Total articles Locally: {count}")
        
        # 2. Check flags
        cur.execute("SELECT flag, count(*) FROM news_articles GROUP BY flag")
        results = cur.fetchall()
        print("Article status flags Locally:")
        for r in results:
            print(f"  {r[0]}: {r[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"FAILED to connect to Local DB: {e}")

if __name__ == "__main__":
    check_local()
