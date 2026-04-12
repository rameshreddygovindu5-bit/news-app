-- =============================================
-- NEWS AGGREGATION PLATFORM - DATABASE SCHEMA
-- =============================================

-- Extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================
-- 1. NEWS SOURCES TABLE
-- =============================================
CREATE TABLE news_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    url VARCHAR(500) NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    scraper_type VARCHAR(20) NOT NULL DEFAULT 'rss',
    scraper_config JSONB DEFAULT '{}',
    scrape_interval_minutes INTEGER NOT NULL DEFAULT 60,
    ai_processing_interval_minutes INTEGER NOT NULL DEFAULT 30,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_paused BOOLEAN NOT NULL DEFAULT FALSE,
    credibility_score FLOAT DEFAULT 0.5,
    priority INTEGER DEFAULT 0,
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- 2. NEWS ARTICLES TABLE
-- =============================================
CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES news_sources(id) ON DELETE CASCADE,
    
    -- Original content
    original_title TEXT NOT NULL,
    original_content TEXT,
    original_url VARCHAR(1000) UNIQUE,
    original_language VARCHAR(10) DEFAULT 'en',
    published_at TIMESTAMP WITH TIME ZONE,
    
    -- Translated content
    translated_title TEXT,
    translated_content TEXT,
    
    -- AI-rephrased content
    rephrased_title TEXT,
    rephrased_content TEXT,
    
    -- Categorization
    category VARCHAR(100),
    slug VARCHAR(500) UNIQUE,
    tags TEXT[] DEFAULT '{}',

    -- Social Media Posting Flags
    is_posted_fb BOOLEAN DEFAULT FALSE,
    is_posted_ig BOOLEAN DEFAULT FALSE,
    is_posted_x BOOLEAN DEFAULT FALSE,
    is_posted_wa BOOLEAN DEFAULT FALSE,
    
    -- Duplicate detection
    content_hash VARCHAR(64) NOT NULL,
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    duplicate_of_id INTEGER REFERENCES news_articles(id),
    
    -- Processing flag: P=Pending Approval, N=New, A=AI Processed, Y=Top News, D=Deleted
    flag CHAR(1) NOT NULL DEFAULT 'N' CHECK (flag IN ('P', 'N', 'A', 'Y', 'D')),
    
    -- AI status and error tracking
    ai_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    ai_error_count INTEGER NOT NULL DEFAULT 0,

    -- Submission tracking
    submitted_by VARCHAR(100),
    
    -- Ranking
    rank_score FLOAT DEFAULT 0,
    
    -- Metadata
    image_url VARCHAR(1000),
    author VARCHAR(255),
    scrape_metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- =============================================
-- 3. JOB EXECUTION LOG TABLE
-- =============================================
CREATE TABLE job_execution_log (
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
);

-- =============================================
-- 4. SYNC METADATA TABLE
-- =============================================
CREATE TABLE sync_metadata (
    id SERIAL PRIMARY KEY,
    target VARCHAR(50) NOT NULL UNIQUE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_rows_ok INTEGER DEFAULT 0,
    last_rows_err INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- 5. ERROR LOGS TABLES
-- =============================================
CREATE TABLE post_error_log (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    platform VARCHAR(10) NOT NULL,
    error_code VARCHAR(50),
    error_message TEXT,
    attempt_num INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE source_error_log (
    id SERIAL PRIMARY KEY,
    source_id INTEGER,
    run_id VARCHAR(50),
    error_type VARCHAR(50),
    error_message TEXT,
    http_status INTEGER,
    url VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- 6. AMIN USERS TABLE
-- =============================================
CREATE TABLE admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'admin',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- 7. CATEGORIES TABLE
-- =============================================
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    article_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- INDEXES
-- =============================================
CREATE INDEX idx_articles_flag ON news_articles(flag);
CREATE INDEX idx_articles_source ON news_articles(source_id);
CREATE INDEX idx_articles_category ON news_articles(category);
CREATE INDEX idx_articles_hash ON news_articles(content_hash);
CREATE INDEX idx_articles_published ON news_articles(published_at DESC);
CREATE INDEX idx_articles_created ON news_articles(created_at DESC);
CREATE INDEX idx_articles_duplicate ON news_articles(is_duplicate);
CREATE INDEX idx_articles_rank ON news_articles(rank_score DESC);
CREATE INDEX idx_articles_slug ON news_articles(slug);
CREATE INDEX idx_articles_tags ON news_articles USING GIN(tags);
CREATE INDEX idx_articles_title_trgm ON news_articles USING GIN(original_title gin_trgm_ops);
CREATE INDEX idx_articles_ai_status ON news_articles(ai_status);
CREATE INDEX idx_job_logs_name ON job_execution_log(job_name);
CREATE INDEX idx_job_logs_status ON job_execution_log(status);

-- =============================================
-- SEED DATA - Default Categories
-- =============================================
INSERT INTO categories (name, slug, description) VALUES
    ('Home', 'home', 'Top stories and general news'),
    ('World', 'world', 'International and global affairs'),
    ('Politics', 'politics', 'Political news and government affairs'),
    ('Business', 'business', 'Business and financial news'),
    ('Tech', 'tech', 'Technology and innovation news'),
    ('Science', 'science', 'Science and research news'),
    ('Health', 'health', 'Health and medical news'),
    ('Entertainment', 'entertainment', 'Movies, film and entertainment news'),
    ('Events', 'events', 'Sports, events and cultural news')
ON CONFLICT (name) DO NOTHING;

-- =============================================
-- SEED DATA - Default Admin User (password: admin123)
-- =============================================
INSERT INTO admin_users (username, password_hash, email, role) VALUES
    ('admin', '$2b$12$LQv3c1yqBo9SkvXS7QTJPOoMQYqRm.EqGvM0Kv5kG.QE8WJnX7Wmy', 'admin@newsplatform.com', 'admin')
ON CONFLICT (username) DO NOTHING;

-- =============================================
-- UPDATE TRIGGER
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_news_sources_updated_at
    BEFORE UPDATE ON news_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_news_articles_updated_at
    BEFORE UPDATE ON news_articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
