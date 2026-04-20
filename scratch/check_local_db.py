
import sqlite3
conn = sqlite3.connect('news-platform-final/backend/newsagg.db')
cur = conn.cursor()
cur.execute("SELECT job_name, status, error_summary, started_at FROM job_execution_log ORDER BY started_at DESC LIMIT 10")
print("Recent Jobs:")
for r in cur.fetchall():
    print(r)
conn.close()
