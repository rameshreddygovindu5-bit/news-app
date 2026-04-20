import psycopg2
from app.config import get_settings
s = get_settings()
try:
    conn = psycopg2.connect(host=s.AWS_DB_HOST, port=s.AWS_DB_PORT, dbname=s.AWS_DB_NAME, user=s.AWS_DB_USER, password=s.AWS_DB_PASSWORD)
    cur = conn.cursor()
    cur.execute("SELECT id, name, is_enabled FROM news_sources")
    rows = cur.fetchall()
    print("AWS News Sources:")
    for r in rows:
        print(f"ID={r[0]}, Name={r[1]}, Enabled={r[2]}")
    cur.close(); conn.close()
except Exception as e:
    print(f"Error: {e}")
