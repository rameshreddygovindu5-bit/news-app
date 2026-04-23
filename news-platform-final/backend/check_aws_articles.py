import psycopg2
from app.config import get_settings

settings = get_settings()

def check_aws():
    try:
        conn = psycopg2.connect(
            host=settings.AWS_DB_HOST,
            port=settings.AWS_DB_PORT,
            dbname=settings.AWS_DB_NAME,
            user=settings.AWS_DB_USER,
            password=settings.AWS_DB_PASSWORD,
            connect_timeout=10
        )
        cur = conn.cursor()
        cur.execute("SELECT flag, count(*) FROM news_articles GROUP BY flag")
        print(f"AWS Article Flags: {cur.fetchall()}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"AWS Error: {e}")

if __name__ == "__main__":
    check_aws()
