import psycopg2
from app.config import get_settings
s = get_settings()
url = "https://www.aljazeera.com/video/newsfeed/2026/4/17/southern-lebanons-only-functioning-hospital-damaged-by-israeli-strikes?traffic_source=rss"
try:
    conn = psycopg2.connect(host=s.AWS_DB_HOST, port=s.AWS_DB_PORT, dbname=s.AWS_DB_NAME, user=s.AWS_DB_USER, password=s.AWS_DB_PASSWORD)
    cur = conn.cursor()
    cur.execute("SELECT id, flag, updated_at FROM news_articles WHERE original_url = %s", (url,))
    row = cur.fetchone()
    if row:
        print(f"AWS Article: ID={row[0]}, Flag='{row[1]}', UpdatedAt={row[2]}")
    else:
        print("Article not found in AWS")
    cur.close(); conn.close()
except Exception as e:
    print(f"Error: {e}")
