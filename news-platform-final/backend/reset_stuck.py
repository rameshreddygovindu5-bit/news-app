#!/usr/bin/env python3
"""
Reset stuck/failed articles so they get reprocessed by Gemini AI.

Run this ONCE after deploying the fix:
    cd news-platform-final/backend
    python reset_stuck.py

This resets:
  1. All "processing" articles (stuck from crashed workers)
  2. All "REWRITE_FAILED" articles (processed by local Seq2Seq only — low quality)
  3. All "failed" articles (errored out)

After running, restart the backend server — Gemini will process all articles automatically.
"""
import sqlite3, sys

db_path = "newsagg.db"
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Count what we are going to reset
    cur.execute("SELECT ai_status, COUNT(*) FROM news_articles GROUP BY ai_status")
    print("Current ai_status distribution:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    # Reset processing (stuck) + REWRITE_FAILED (low quality) + failed (errored)
    reset_statuses = ("processing", "REWRITE_FAILED", "failed", "unknown")
    cur.execute(
        f"UPDATE news_articles SET ai_status='pending', ai_error_count=0 "
        f"WHERE ai_status IN ({','.join('?' * len(reset_statuses))})",
        reset_statuses
    )
    conn.commit()
    n = cur.rowcount

    print(f"\n✅ Reset {n} articles → pending (ready for Gemini AI)")
    print("\nNew distribution:")
    cur.execute("SELECT ai_status, COUNT(*) FROM news_articles GROUP BY ai_status")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")
    print("\nRestart the backend server — Gemini will process all articles automatically.")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
