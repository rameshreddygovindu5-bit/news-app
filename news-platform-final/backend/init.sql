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
    language VARCHAR(10) NOT NULL DEFAULT 'en',  -- 'te' for Telugu, 'en' for English
    scraper_type VARCHAR(20) NOT NULL DEFAULT 'rss',  -- 'rss', 'html', 'api'
    scraper_config JSONB DEFAULT '{}',  -- Additional config for scraper
    scrape_interval_minutes INTEGER NOT NULL DEFAULT 60,
    ai_processing_interval_minutes INTEGER NOT NULL DEFAULT 30,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_paused BOOLEAN NOT NULL DEFAULT FALSE,
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
    
    -- Processing flags: P=Pending Approval, N=New, A=AI Processed, Y=Top News, D=Deleted
    flag CHAR(1) NOT NULL DEFAULT 'N' CHECK (flag IN ('P', 'N', 'A', 'Y', 'D')),
    
    -- AI error tracking (skip after 3 failures)
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
-- 3. SCHEDULER LOGS TABLE
-- =============================================
CREATE TABLE scheduler_logs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,  -- 'scrape', 'ai_process', 'ranking', 'cleanup'
    source_id INTEGER REFERENCES news_sources(id),
    status VARCHAR(20) NOT NULL DEFAULT 'started',  -- 'started', 'completed', 'failed'
    articles_processed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT
);

-- =============================================
-- 4. ADMIN USERS TABLE
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
-- 5. CATEGORIES TABLE
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
CREATE INDEX idx_scheduler_logs_type ON scheduler_logs(job_type);
CREATE INDEX idx_scheduler_logs_status ON scheduler_logs(status);

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

-- Migrate old category names to new ones
UPDATE news_articles SET category = 'Tech' WHERE category IN ('Technology', 'technology');
UPDATE news_articles SET category = 'Entertainment' WHERE category IN ('Movies', 'movies', 'Entertainment');
UPDATE news_articles SET category = 'World' WHERE category IN ('International', 'international');
UPDATE news_articles SET category = 'Events' WHERE category IN ('Sports', 'sports');
UPDATE news_articles SET category = 'Home' WHERE category IN ('General', 'general');

-- =============================================
-- SEED DATA - Default News Sources
-- =============================================
INSERT INTO news_sources (name, url, language, scraper_type, scraper_config, scrape_interval_minutes, is_enabled, is_paused) VALUES
    -- Dedicated Telugu Scrapers
    ('GreatAndhra', 'https://www.greatandhra.com', 'en', 'html', '{"sections": ["latest", "latest/2"], "max_articles": 30}', 60, TRUE, FALSE),
    ('Eenadu', 'https://www.eenadu.net', 'te', 'html', '{"max_articles": 30}', 120, TRUE, FALSE),
    ('Sakshi', 'https://www.sakshi.com', 'te', 'html', '{"max_articles": 30}', 120, TRUE, FALSE),
    ('TV9 Telugu', 'https://www.tv9telugu.com', 'te', 'html', '{"max_articles": 25}', 90, TRUE, FALSE),
    ('PrabhaNews', 'https://www.prabhanews.com', 'te', 'html', '{"rss_url": "https://www.prabhanews.com/feed/", "max_articles": 25}', 90, TRUE, FALSE),
    ('Telugu123', 'https://www.telugu123.com', 'te', 'html', '{"max_articles": 20}', 120, TRUE, FALSE),
    ('TeluguTimes Telugu', 'https://www.telugutimes.net', 'te', 'html', '{"base_url": "https://www.telugutimes.net", "rss_url": "https://www.telugutimes.net/feed/", "max_articles": 20}', 120, TRUE, FALSE),
    ('TeluguTimes English', 'https://www.telugutimes.net/english', 'en', 'html', '{"base_url": "https://www.telugutimes.net/english", "rss_url": "https://www.telugutimes.net/english/feed/", "max_articles": 20}', 120, TRUE, FALSE),
    -- Dedicated English Scrapers
    ('OneIndia English', 'https://www.oneindia.com', 'en', 'rss', '{"rss_url": "https://www.oneindia.com/rss/news-fb.xml", "max_articles": 25}', 60, TRUE, FALSE),
    ('OneIndia Telugu', 'https://telugu.oneindia.com', 'te', 'rss', '{"rss_url": "https://telugu.oneindia.com/rss/feeds/oneindia-telugu.xml", "max_articles": 25}', 60, TRUE, FALSE),
    ('AlJazeera', 'https://www.aljazeera.com', 'en', 'rss', '{"rss_url": "https://www.aljazeera.com/xml/rss/all.xml", "max_articles": 20}', 60, TRUE, FALSE),
    -- RSS English Sources
    ('NDTV', 'https://www.ndtv.com', 'en', 'rss', '{"rss_url": "https://feeds.feedburner.com/ndtvnews-top-stories", "max_articles": 20}', 30, TRUE, FALSE),
    ('The Hindu', 'https://www.thehindu.com', 'en', 'rss', '{"rss_url": "https://www.thehindu.com/feeder/default.rss", "max_articles": 20}', 30, TRUE, FALSE),
    ('Times of India', 'https://timesofindia.indiatimes.com', 'en', 'rss', '{"rss_url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "max_articles": 20}', 30, TRUE, FALSE),
    ('Indian Express', 'https://indianexpress.com', 'en', 'rss', '{"rss_url": "https://indianexpress.com/feed/", "max_articles": 20}', 30, TRUE, FALSE),
    ('ANI News', 'https://www.aninews.in', 'en', 'rss', '{"rss_url": "https://www.aninews.in/rss/national.xml", "max_articles": 20}', 30, TRUE, FALSE),
    ('BBC India', 'https://www.bbc.com/news/world/asia/india', 'en', 'rss', '{"rss_url": "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml", "max_articles": 15}', 60, TRUE, FALSE),
    ('Reuters India', 'https://www.reuters.com', 'en', 'rss', '{"rss_url": "https://www.reuters.com/rssFeed/worldNews", "max_articles": 15}', 60, TRUE, FALSE),
    ('Samayam Telugu', 'https://telugu.samayam.com', 'te', 'rss', '{"rss_url": "https://telugu.samayam.com/rssfeed.cms", "max_articles": 15}', 60, TRUE, FALSE),
    -- Manual
    ('Peoples Feedback', 'https://www.peoples-feedback.com', 'en', 'manual', '{}', 0, TRUE, FALSE)
ON CONFLICT (name) DO NOTHING;

-- =============================================
-- SEED DATA - Default Admin User (password: admin123)
-- =============================================
INSERT INTO admin_users (username, password_hash, email, role) VALUES
    ('admin', '$2b$12$LQv3c1yqBo9SkvXS7QTJPOoMQYqRm.EqGvM0Kv5kG.QE8WJnX7Wmy', 'admin@newsplatform.com', 'admin');

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
