import asyncio
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def init_db():
    conn_str = "host=localhost dbname=postgres user=postgres password=NewStrongPassword123 port=5432"
    try:
        conn = psycopg2.connect(conn_str)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname='news_db_fe'")
        exists = cur.fetchone()
        if not exists:
            print("Creating database news_db_fe...")
            cur.execute("CREATE DATABASE news_db_fe")
        else:
            print("Database news_db_fe already exists.")
        
        cur.close()
        conn.close()
        
        # Connect to news_db_fe and run init.sql
        conn_str_fe = "host=localhost dbname=news_db_fe user=postgres password=NewStrongPassword123 port=5432"
        conn = psycopg2.connect(conn_str_fe)
        cur = conn.cursor()
        
        with open('init.sql', 'r', encoding='utf-8') as f:
            sql = f.read()
            # Split by semi-colon might be tricky if there are strings with semi-colon, 
            # but for this init.sql it might work or we can just try executing the whole thing if it's safe.
            # psycopg2.execute can handle multiple statements if they are separated.
            try:
                cur.execute(sql)
                conn.commit()
                print("Successfully initialized database schema.")
            except Exception as e:
                print(f"Error executing SQL: {e}")
                conn.rollback()
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Database connection error: {e}")

if __name__ == "__main__":
    init_db()
