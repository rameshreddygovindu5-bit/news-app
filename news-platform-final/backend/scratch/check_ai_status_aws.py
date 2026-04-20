import psycopg2
from app.config import get_settings
s = get_settings()
try:
    conn = psycopg2.connect(host=s.AWS_DB_HOST, port=s.AWS_DB_PORT, dbname=s.AWS_DB_NAME, user=s.AWS_DB_USER, password=s.AWS_DB_PASSWORD)
    cur = conn.cursor()
    cur.execute("SELECT ai_status, COUNT(*) FROM news_articles GROUP BY ai_status")
    rows = cur.fetchall()
    print("AWS AI Status Counts:")
    for r in rows:
        print(f"Status={r[0]}, Count={r[1]}")
    cur.close(); conn.close()
except Exception as e:
    print(f"Error: {e}")
