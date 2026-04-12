import asyncio
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

from urllib.parse import urlparse

load_dotenv()

def init_db():
    # Try to get connection string from .env
    db_url = os.getenv("DATABASE_URL_SYNC")
    if not db_url:
        print("Error: DATABASE_URL_SYNC not found in .env")
        return

    try:
        # 1. Connect and initialize schema
        # psycopg2 can handle the postgres:// connection string directly
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print(f"Connecting to {db_url.split('@')[-1]}...")
        
        with open('init.sql', 'r', encoding='utf-8') as f:
            sql = f.read()
            try:
                cur.execute(sql)
                conn.commit()
                print("✅ Successfully initialized database schema.")
            except Exception as e:
                print(f"⚠️ Error executing SQL: {e}")
                conn.rollback()
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")

if __name__ == "__main__":
    init_db()
