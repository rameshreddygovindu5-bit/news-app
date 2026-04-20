import psycopg2
from app.config import get_settings
s = get_settings()
try:
    conn = psycopg2.connect(
        host=s.AWS_DB_HOST, port=s.AWS_DB_PORT, 
        dbname=s.AWS_DB_NAME, user=s.AWS_DB_USER, 
        password=s.AWS_DB_PASSWORD
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM news_articles WHERE flag='Y'")
    print(f"AWS Articles with flag=Y: {cur.fetchone()[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
