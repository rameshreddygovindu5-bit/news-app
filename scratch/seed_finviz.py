import os
import sys
import sqlite3
import json

# DB Path
DB_PATH = os.path.join('news-platform-final', 'backend', 'newsagg.db')

def seed():
    source_data = {
        "name": "Finviz Market News",
        "url": "https://finviz.com/news.ashx",
        "language": "en",
        "scraper_type": "finviz",
        "scrape_interval_minutes": 15,
        "ai_processing_interval_minutes": 5,
        "is_enabled": 1,
        "is_paused": 0,
        "credibility_score": 0.88,
        "priority": 2,
        "scraper_config": {
            "max_articles": 50, "skip_paywalled": True, "min_content_length": 150,
            "fetch_delay_seconds": 0.6, "target_category": "Business", "fetch_full_content": True,
        },
    }
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news_sources';")
    if not cur.fetchone():
        print("Error: news_sources table not found in database.")
        conn.close()
        return

    cur.execute("SELECT id FROM news_sources WHERE url=?", (source_data["url"],))
    if not cur.fetchone():
        cur.execute("""INSERT INTO news_sources 
            (name, url, language, scraper_type, scrape_interval_minutes, ai_processing_interval_minutes, is_enabled, is_paused, credibility_score, priority, scraper_config) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (source_data["name"], source_data["url"], source_data["language"], source_data["scraper_type"], 15, 5, 1, 0, 0.88, 2, json.dumps(source_data["scraper_config"])))
        conn.commit()
        print(f"✓ Added 'Finviz Market News' to {DB_PATH} (ID: {cur.lastrowid})")
    else:
        print(f"ℹ 'Finviz Market News' already exists in {DB_PATH}")
    
    conn.close()

if __name__ == "__main__":
    seed()
