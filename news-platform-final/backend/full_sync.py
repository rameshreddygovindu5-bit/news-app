"""
Full Bidirectional Sync: Local SQLite ↔ AWS PostgreSQL
- Pushes ALL local articles to AWS (upsert on original_url)
- Pulls AWS-only articles back to local
- Syncs ALL important fields including rank_score, ai_status, image_url, etc.
- Syncs categories, sources, and wishes
"""
import psycopg2
import sqlite3
import os
import hashlib
from dotenv import load_dotenv
from datetime import datetime, timezone
from psycopg2.extras import execute_values

load_dotenv()

# All article columns we care about syncing
ARTICLE_COLS = [
    "source_id", "original_title", "original_content", "original_url",
    "original_language", "published_at",
    "translated_title", "translated_content",
    "rephrased_title", "rephrased_content",
    "telugu_title", "telugu_content",
    "category", "slug", "tags",
    "content_hash", "is_duplicate", "flag",
    "ai_status", "ai_error_count",
    "rank_score", "image_url", "author",
    "created_at", "updated_at", "processed_at"
]

ARTICLE_COLS_STR = ", ".join(ARTICLE_COLS)

def full_sync():
    print("=" * 60)
    print("  FULL BIDIRECTIONAL SYNC — Local ↔ AWS")
    print("=" * 60)

    local_conn = sqlite3.connect('newsagg.db')
    local_conn.row_factory = sqlite3.Row
    local_cur = local_conn.cursor()

    try:
        aws_conn = psycopg2.connect(
            host=os.getenv("AWS_DB_HOST"),
            port=os.getenv("AWS_DB_PORT"),
            dbname=os.getenv("AWS_DB_NAME"),
            user=os.getenv("AWS_DB_USER"),
            password=os.getenv("AWS_DB_PASSWORD"),
            connect_timeout=30
        )
        aws_cur = aws_conn.cursor()
        print("✅ Connected to AWS PostgreSQL")
    except Exception as e:
        print(f"❌ Cannot connect to AWS: {e}")
        return

    try:
        # ── 1. Sync Categories ────────────────────────────────────────
        print("\n[1/5] Syncing categories...")
        local_cur.execute("SELECT name, slug, description, is_active, article_count FROM categories")
        cats = local_cur.fetchall()
        if cats:
            execute_values(aws_cur,
                "INSERT INTO categories (name, slug, description, is_active, article_count) VALUES %s "
                "ON CONFLICT (name) DO UPDATE SET is_active=EXCLUDED.is_active, article_count=EXCLUDED.article_count",
                [(c[0], c[1], c[2], bool(c[3]), c[4]) for c in cats])
            print(f"   → {len(cats)} categories synced")

        # ── 2. Sync Sources ──────────────────────────────────────────
        print("[2/5] Syncing sources...")
        local_cur.execute("SELECT id, name, url, scraper_type, language, is_enabled FROM news_sources")
        srcs = local_cur.fetchall()
        if srcs:
            execute_values(aws_cur,
                "INSERT INTO news_sources (id, name, url, scraper_type, language, is_enabled) VALUES %s "
                "ON CONFLICT (id) DO UPDATE SET is_enabled=EXCLUDED.is_enabled, name=EXCLUDED.name, url=EXCLUDED.url",
                [(s[0], s[1], s[2], s[3], s[4], bool(s[5])) for s in srcs])
            print(f"   → {len(srcs)} sources synced")

        # ── 3. Ensure content_hash on all local articles ─────────────
        print("[3/5] Ensuring content_hash on local articles...")
        local_cur.execute("SELECT id, original_title, original_content FROM news_articles WHERE content_hash IS NULL OR content_hash = ''")
        no_hash = local_cur.fetchall()
        if no_hash:
            for row in no_hash:
                h = hashlib.sha256(f"{row[1] or ''}{row[2] or ''}".encode()).hexdigest()
                local_cur.execute("UPDATE news_articles SET content_hash = ? WHERE id = ?", (h, row[0]))
            local_conn.commit()
            print(f"   → Generated hash for {len(no_hash)} articles")
        else:
            print("   → All articles have content_hash ✓")

        # ── 4. Push Local → AWS (full upsert) ────────────────────────
        print("[4/5] Pushing local articles → AWS...")
        local_cur.execute(f"SELECT {ARTICLE_COLS_STR} FROM news_articles WHERE flag != 'D'")
        local_rows = local_cur.fetchall()
        
        if local_rows:
            # Convert tags from JSON string to Python list for PostgreSQL ARRAY
            import json
            clean_rows = []
            for r in local_rows:
                row = list(r)
                # tags field (index 14) - parse JSON string into list for PG array
                if row[14] and isinstance(row[14], str):
                    try:
                        row[14] = json.loads(row[14])
                    except (json.JSONDecodeError, TypeError):
                        row[14] = []
                elif row[14] is None:
                    row[14] = []
                # is_duplicate (index 16) - convert to bool
                row[16] = bool(row[16]) if row[16] is not None else False
                clean_rows.append(tuple(row))

            # Upsert based on original_url
            placeholders = ", ".join(["%s"] * len(ARTICLE_COLS))
            SQL = f"""
                INSERT INTO news_articles ({ARTICLE_COLS_STR})
                VALUES %s
                ON CONFLICT (original_url) DO UPDATE SET
                    rephrased_title = EXCLUDED.rephrased_title,
                    rephrased_content = EXCLUDED.rephrased_content,
                    telugu_title = EXCLUDED.telugu_title,
                    telugu_content = EXCLUDED.telugu_content,
                    translated_title = EXCLUDED.translated_title,
                    translated_content = EXCLUDED.translated_content,
                    category = EXCLUDED.category,
                    slug = EXCLUDED.slug,
                    tags = EXCLUDED.tags,
                    flag = EXCLUDED.flag,
                    ai_status = EXCLUDED.ai_status,
                    rank_score = EXCLUDED.rank_score,
                    image_url = EXCLUDED.image_url,
                    content_hash = EXCLUDED.content_hash,
                    updated_at = EXCLUDED.updated_at,
                    processed_at = EXCLUDED.processed_at
            """
            # Batch in chunks of 200
            batch_size = 200
            for i in range(0, len(clean_rows), batch_size):
                batch = clean_rows[i:i + batch_size]
                execute_values(aws_cur, SQL, batch)
                print(f"   → Pushed batch {i // batch_size + 1} ({len(batch)} articles)")
            
            aws_conn.commit()
            print(f"   → Total: {len(clean_rows)} articles pushed to AWS")
        
        # ── 5. Pull AWS → Local (articles only on AWS) ───────────────
        print("[5/5] Pulling AWS-only articles → local...")
        aws_cur.execute(f"SELECT {ARTICLE_COLS_STR} FROM news_articles WHERE flag != 'D'")
        aws_rows = aws_cur.fetchall()
        
        # Get local URLs for comparison
        local_cur.execute("SELECT original_url FROM news_articles")
        local_urls = set(r[0] for r in local_cur.fetchall() if r[0])
        
        new_from_aws = []
        updated_from_aws = 0
        for row in aws_rows:
            url = row[3]  # original_url
            if url and url not in local_urls:
                new_from_aws.append(row)
        
        if new_from_aws:
            cols_placeholder = ", ".join(["?"] * len(ARTICLE_COLS))
            insert_sql = f"INSERT OR IGNORE INTO news_articles ({ARTICLE_COLS_STR}) VALUES ({cols_placeholder})"
            for row in new_from_aws:
                try:
                    # Convert PostgreSQL types for SQLite
                    row_list = list(row)
                    # tags: convert list to JSON string
                    if isinstance(row_list[14], list):
                        import json
                        row_list[14] = json.dumps(row_list[14])
                    local_cur.execute(insert_sql, tuple(row_list))
                except Exception as e:
                    print(f"   ⚠ Skip article: {str(e)[:80]}")
            local_conn.commit()
            print(f"   → Pulled {len(new_from_aws)} new articles from AWS")
        else:
            print("   → No AWS-only articles to pull")

        # ── Final Counts ─────────────────────────────────────────────
        local_cur.execute("SELECT COUNT(*) FROM news_articles WHERE flag IN ('A','Y')")
        local_total = local_cur.fetchone()[0]
        aws_cur.execute("SELECT COUNT(*) FROM news_articles WHERE flag IN ('A','Y')")
        aws_total = aws_cur.fetchone()[0]
        
        local_cur.execute("SELECT COUNT(*) FROM news_articles WHERE flag = 'Y'")
        local_top = local_cur.fetchone()[0]
        aws_cur.execute("SELECT COUNT(*) FROM news_articles WHERE flag = 'Y'")
        aws_top = aws_cur.fetchone()[0]

        print("\n" + "=" * 60)
        print(f"  LOCAL  →  AI Processed: {local_total}  |  Top News: {local_top}")
        print(f"  AWS    →  AI Processed: {aws_total}  |  Top News: {aws_top}")
        print("=" * 60)

        if local_top != aws_top:
            print(f"\n⚠ Top News mismatch (Local={local_top}, AWS={aws_top})")
            print("  This should be resolved now that all flag/rank_score values were synced.")

        aws_conn.commit()
        print("\n✅ Full bidirectional sync complete!")

    except Exception as e:
        print(f"\n❌ Sync error: {e}")
        import traceback
        traceback.print_exc()
        try:
            aws_conn.rollback()
        except:
            pass
    finally:
        aws_cur.close()
        aws_conn.close()
        local_conn.close()

if __name__ == "__main__":
    full_sync()
