
import sqlite3
import os

db_path = "c:\\Ramesh\\news-app\\04152026\\news-platform-final\\backend\\newsagg.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("AI Status Counts:")
cur.execute("SELECT ai_status, count(*) FROM news_articles GROUP BY ai_status")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\nFlags Counts:")
cur.execute("SELECT flag, count(*) FROM news_articles GROUP BY flag")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
