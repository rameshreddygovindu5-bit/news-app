import sqlite3
import os

db_path = r"c:\Ramesh\news-app\04152026\news-platform-final\backend\newsagg.db"

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    print("Applying additional composite indices...")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_articles_flag_created ON news_articles (flag, created_at);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_articles_flag_rank ON news_articles (flag, rank_score);")
    conn.commit()
    print("Indices applied successfully.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error applying indices: {e}")
    exit(1)
