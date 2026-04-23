import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv("AWS_DB_HOST"),
        port=os.getenv("AWS_DB_PORT"),
        dbname=os.getenv("AWS_DB_NAME"),
        user=os.getenv("AWS_DB_USER"),
        password=os.getenv("AWS_DB_PASSWORD"),
        connect_timeout=10
    )
    cur = conn.cursor()
    
    cur.execute("SELECT count(*) FROM news_articles")
    count = cur.fetchone()[0]
    print(f"Total articles in AWS: {count}")
    
    cur.execute("SELECT flag, count(*) FROM news_articles GROUP BY flag")
    print(f"Flags in AWS: {cur.fetchall()}")
    
    cur.execute("SELECT original_language, count(*) FROM news_articles GROUP BY original_language")
    print(f"Languages in AWS: {cur.fetchall()}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error connecting to AWS: {e}")
