import sqlite3
import os

db_path = "newsagg.db"

if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Disable foreign key checks temporarily if needed, or just delete in order
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        print("Cleaning up database...")
        
        # Delete articles
        cursor.execute("DELETE FROM news_articles;")
        print("Deleted all articles.")
        
        # Delete logs
        cursor.execute("DELETE FROM job_execution_log;")
        cursor.execute("DELETE FROM status_log;") if "status_log" in [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")] else None
        cursor.execute("DELETE FROM source_error_log;")
        cursor.execute("DELETE FROM post_error_log;")
        
        # Optional: Reset sync metadata
        cursor.execute("DELETE FROM sync_metadata;")
        
        conn.commit()
        conn.execute("VACUUM;")
        conn.close()
        print("Database cleanup complete.")
    except Exception as e:
        print(f"Error cleaning database: {e}")
