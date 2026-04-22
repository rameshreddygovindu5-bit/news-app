import sqlite3
conn = sqlite3.connect('newsagg.db')
cursor = conn.cursor()
cursor.execute("SELECT flag, count(*) FROM news_articles GROUP BY flag")
print(cursor.fetchall())
cursor.execute("SELECT ai_status, count(*) FROM news_articles GROUP BY ai_status")
print(cursor.fetchall())
conn.close()
