import psycopg2
import sys

host = "32.193.27.142"
port = 5432
dbname = "news_db_fe"
user = "appuser"
password = "PF2026Secure!@#"

try:
    print(f"Connecting to {host}...")
    conn = psycopg2.connect(
        host=host, port=port, dbname=dbname, user=user, password=password,
        connect_timeout=10, sslmode='require'
    )
    print("Connection successful!")
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(f"PostgreSQL version: {cur.fetchone()[0]}")
    cur.execute("SELECT count(*) FROM news_articles;")
    print(f"Article count: {cur.fetchone()[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)
