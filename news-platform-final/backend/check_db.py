import sqlite3
import os

db_path = 'newsagg.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("SELECT flag, original_language, count(*) FROM news_articles GROUP BY flag, original_language;")
    rows = cursor.fetchall()
    print("Flag | Language | Count")
    print("-" * 30)
    for row in rows:
        print(f"{row[0]} | {row[1]} | {row[2]}")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
