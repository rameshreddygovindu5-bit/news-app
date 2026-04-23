#!/usr/bin/env python3
"""
Fix content_hash for all articles that don't have it
"""
import sqlite3
import hashlib

def fix_content_hashes():
    conn = sqlite3.connect('newsagg.db')
    cur = conn.cursor()
    
    # Find all articles without content_hash
    cur.execute("SELECT id, original_title, original_content FROM news_articles WHERE content_hash IS NULL OR content_hash = ''")
    articles = cur.fetchall()
    
    if not articles:
        print("✅ All articles already have content_hash")
        return
    
    print(f"🔧 Fixing {len(articles)} articles without content_hash...")
    
    for art_id, title, content in articles:
        # Generate hash from title + content
        hash_input = f"{title or ''}{content or ''}"
        content_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        
        # Update the article
        cur.execute("UPDATE news_articles SET content_hash = ? WHERE id = ?", (content_hash, art_id))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Fixed {len(articles)} articles")

if __name__ == "__main__":
    fix_content_hashes()
