"""
AWS DB Migration Script
=======================
Safely adds all new columns to the existing AWS PostgreSQL schema.
Run once on the EC2 instance:  python migrate_aws.py
All ALTER TABLE commands use IF NOT EXISTS so they are safe to re-run.
"""
import os, sys
import psycopg2

DB_URL = os.environ.get("AWS_DATABASE_URL") or \
         "postgresql://appuser:PF2026Secure%21%40%23@32.193.27.142:5432/news_db_fe"

MIGRATIONS = [
    # ── news_articles new columns ───────────────────────────────────────
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS submitted_by VARCHAR(100)",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS telugu_title TEXT",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS telugu_content TEXT",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS ai_error_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS rank_score FLOAT DEFAULT 0",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS image_url VARCHAR(1000)",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS author VARCHAR(255)",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS scrape_metadata JSONB DEFAULT '{}'",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS is_posted_fb BOOLEAN DEFAULT FALSE",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS is_posted_ig BOOLEAN DEFAULT FALSE",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS is_posted_x  BOOLEAN DEFAULT FALSE",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS is_posted_wa BOOLEAN DEFAULT FALSE",
    # Flag constraint — drop old, add new that includes 'P'
    "ALTER TABLE news_articles DROP CONSTRAINT IF EXISTS valid_flag",
    "ALTER TABLE news_articles ADD CONSTRAINT valid_flag CHECK (flag IN ('P','N','A','Y','D'))",

    # ── news_sources new columns ────────────────────────────────────────
    "ALTER TABLE news_sources ADD COLUMN IF NOT EXISTS credibility_score FLOAT DEFAULT 0.5",
    "ALTER TABLE news_sources ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0",
    "ALTER TABLE news_sources ADD COLUMN IF NOT EXISTS is_paused BOOLEAN NOT NULL DEFAULT FALSE",

    # ── admin_users ─────────────────────────────────────────────────────
    "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'admin'",
    "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS email VARCHAR(255)",

    # ── categories ──────────────────────────────────────────────────────
    "ALTER TABLE categories ADD COLUMN IF NOT EXISTS article_count INTEGER DEFAULT 0",

    # ── polls (new tables) ──────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS polls (
        id SERIAL PRIMARY KEY,
        question VARCHAR(500) NOT NULL,
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        expires_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS poll_options (
        id SERIAL PRIMARY KEY,
        poll_id INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
        option_text VARCHAR(255) NOT NULL,
        votes_count INTEGER DEFAULT 0
    )
    """,

    # ── sync_metadata ────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS sync_metadata (
        id SERIAL PRIMARY KEY,
        target VARCHAR(50) NOT NULL UNIQUE,
        last_sync_at TIMESTAMP WITH TIME ZONE,
        last_rows_ok INTEGER DEFAULT 0,
        last_rows_err INTEGER DEFAULT 0,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── source_error_log ─────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS source_error_log (
        id SERIAL PRIMARY KEY,
        source_id INTEGER,
        run_id VARCHAR(50),
        error_type VARCHAR(50),
        error_message TEXT,
        http_status INTEGER,
        url VARCHAR(1000),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── Indexes ──────────────────────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_articles_flag ON news_articles(flag)",
    "CREATE INDEX IF NOT EXISTS idx_articles_ai_status ON news_articles(ai_status)",
    "CREATE INDEX IF NOT EXISTS idx_articles_slug ON news_articles(slug)",
    "CREATE INDEX IF NOT EXISTS idx_articles_hash ON news_articles(content_hash)",
]

def run():
    print(f"Connecting to AWS DB...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()
    ok = 0
    errors = []

    for sql in MIGRATIONS:
        sql = sql.strip()
        label = sql[:80].replace('\n', ' ')
        try:
            cur.execute(sql)
            conn.commit()
            print(f"  [OK] {label}")
            ok += 1
        except Exception as e:
            conn.rollback()
            print(f"  [WARN] {label}\n     -> {e}")
            errors.append((label, str(e)))

    cur.close()
    conn.close()
    print(f"\n{'='*60}")
    print(f"Migration complete: {ok}/{len(MIGRATIONS)} succeeded, {len(errors)} skipped/failed")
    if errors:
        print("\nSkipped (likely already exist):")
        for lbl, err in errors:
            print(f"  - {lbl[:60]}: {err[:80]}")

if __name__ == "__main__":
    run()
