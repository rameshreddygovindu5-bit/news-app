import sqlite3
import os

db_path = r"c:\Ramesh\news-app\04152026\news-platform-final\backend\newsagg.db"

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    print("Applying indices for performance optimization...")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_articles_lang_flag ON news_articles (original_language, flag);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_articles_pub_date ON news_articles (published_at);")
    conn.commit()
    print("Indices applied successfully.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error applying indices: {e}")
    exit(1)
