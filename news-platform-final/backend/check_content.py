import sqlite3
conn = sqlite3.connect('newsagg.db')
cur = conn.cursor()
cur.execute("SELECT id, original_title, rephrased_title, original_language, ai_status FROM news_articles WHERE flag='Y' LIMIT 5")
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()
