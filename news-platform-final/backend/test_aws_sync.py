#!/usr/bin/env python3
"""
Test AWS Sync functionality
"""
import os
import sys
import psycopg2
import sqlite3
from dotenv import load_dotenv

load_dotenv()

def test_aws_connection():
    """Test AWS DB connection"""
    print("🔍 Testing AWS DB connection...")
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
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print(f"✅ AWS DB Connected: {version[:50]}...")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ AWS DB Connection failed: {e}")
        return False

def test_local_db():
    """Test local SQLite DB"""
    print("🔍 Testing local DB...")
    try:
        conn = sqlite3.connect('newsagg.db')
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM news_articles")
        count = cur.fetchone()[0]
        print(f"✅ Local DB has {count} articles")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Local DB error: {e}")
        return False

def test_sync():
    """Run sync test"""
    print("\n🚀 Starting AWS Sync Test...")
    
    # Check environment variables
    required_vars = ["AWS_DB_HOST", "AWS_DB_PORT", "AWS_DB_NAME", "AWS_DB_USER", "AWS_DB_PASSWORD"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("Please set these in your .env file")
        return False
    
    # Test connections
    if not test_local_db():
        return False
    if not test_aws_connection():
        return False
    
    # Run the sync
    print("\n📤 Running sync...")
    try:
        from sync_articles import sync_articles_fixed
        sync_articles_fixed()
        print("✅ Sync completed successfully")
        return True
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False

if __name__ == "__main__":
    success = test_sync()
    sys.exit(0 if success else 1)
