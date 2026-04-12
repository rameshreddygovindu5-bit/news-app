import psycopg2
from dotenv import load_dotenv

load_dotenv()

def update_db():
    conn_str = "host=localhost dbname=news_db_fe user=postgres password=NewStrongPassword123 port=5432"
    try:
        conn = psycopg2.connect(conn_str)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Add missing columns to news_sources
        try:
            cur.execute("ALTER TABLE news_sources ADD COLUMN credibility_score FLOAT DEFAULT 0.5")
            print("Added credibility_score to news_sources")
        except Exception: pass

        try:
            cur.execute("ALTER TABLE news_sources ADD COLUMN priority INTEGER DEFAULT 0")
            print("Added priority to news_sources")
        except Exception: pass

        # Add missing columns to news_articles
        try:
            cur.execute("ALTER TABLE news_articles ADD COLUMN ai_status VARCHAR(20) DEFAULT 'pending'")
            print("Added ai_status to news_articles")
        except Exception: pass

        # Create missing tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS job_execution_log (
                id SERIAL PRIMARY KEY,
                job_name VARCHAR(100) NOT NULL,
                run_id VARCHAR(50) NOT NULL,
                started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                ended_at TIMESTAMP WITH TIME ZONE,
                status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
                rows_ok INTEGER DEFAULT 0,
                rows_err INTEGER DEFAULT 0,
                duration_s FLOAT,
                error_summary TEXT,
                triggered_by VARCHAR(50) DEFAULT 'cron'
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS post_error_log (
                id SERIAL PRIMARY KEY,
                article_id INTEGER NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
                platform VARCHAR(10) NOT NULL,
                error_code VARCHAR(50),
                error_message TEXT,
                attempt_num INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sync_metadata (
                id SERIAL PRIMARY KEY,
                target VARCHAR(50) NOT NULL UNIQUE,
                last_sync_at TIMESTAMP WITH TIME ZONE,
                last_rows_ok INTEGER DEFAULT 0,
                last_rows_err INTEGER DEFAULT 0,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)

        cur.execute("""
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
        """)

        print("Database schema updated successfully.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    update_db()
