"""
Application Configuration — Single Source of Truth
CATEGORIES must stay in sync with:
  - app/services/category_service.py → CANONICAL_CATEGORIES
  - frontend/src/App.js             → const CATS
  - peoples-feedback-client         → DEFAULT_CATEGORIES / API
"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True, frozen=False, extra='ignore')

    APP_NAME: str = "News Aggregation Platform"
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ── CANONICAL CATEGORIES (master list — keep in sync everywhere) ──
    CATEGORIES: List[str] = [
        "Home", "World", "Politics", "Business", "Tech",
        "Health", "Science", "Entertainment", "Events", "Sports",
        "Surveys", "Polls",
    ]

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://newsadmin:newspass123@localhost:5432/newsagg"
    DATABASE_URL_SYNC: str = "postgresql://newsadmin:newspass123@localhost:5432/newsagg"
    AWS_DB_HOST: str = ""
    AWS_DB_PORT: int = 5432
    AWS_DB_NAME: str = "news_db_fe"
    AWS_DB_USER: str = ""
    AWS_DB_PASSWORD: str = ""

    # ── Redis ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── AI (chain: gemini_primary → gemini_secondary → openai → local → original) ─
    AI_PROVIDER_CHAIN: List[str] = ["gemini", "gemini2", "openai", "local", "original"]
    AI_BATCH_SIZE: int = 50
    AI_CONCURRENCY: int = 8
    AI_MAX_RETRIES: int = 2
    GEMINI_API_KEY: str = ""
    GEMINI_API_KEY_SECONDARY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # ── Scraping ──────────────────────────────────────────────────────
    SCRAPE_TIMEOUT: int = 30
    MAX_ARTICLES_PER_SCRAPE: int = 200
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # ── Ranking ───────────────────────────────────────────────────────
    TOP_NEWS_COUNT: int = 100
    TOP_NEWS_MAX_AGE_DAYS: int = 60
    TOP_NEWS_MAX_PER_CATEGORY: int = 25
    TOP_NEWS_MIN_PER_CATEGORY: int = 20   # guarantee min 20 per category
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.85

    # ── Social Media ──────────────────────────────────────────────────
    SOCIAL_POST_ENABLED: bool = True
    SOCIAL_SITE_URL: str = "https://www.peoples-feedback.com"
    FB_PAGE_ACCESS_TOKEN: str = ""
    FB_PAGE_ID: str = ""
    IG_BUSINESS_ACCOUNT_ID: str = ""
    X_API_KEY: str = ""
    X_API_SECRET: str = ""
    X_ACCESS_TOKEN: str = ""
    X_ACCESS_SECRET: str = ""
    WA_PHONE_NUMBER_ID: str = ""
    WA_ACCESS_TOKEN: str = ""
    WA_RECIPIENT_GROUP: str = ""

    # ── CORS ──────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "https://www.peoples-feedback.com",
    ]

    ENABLED_SOURCES: str = ""

    # ── Scheduler ─────────────────────────────────────────────────────
    SCHEDULER_ENABLED: bool = True
    SCHEDULE_SCRAPE_ENABLED: bool = True
    SCHEDULE_AI_ENABLED: bool = True
    SCHEDULE_RANKING_ENABLED: bool = True
    SCHEDULE_AWS_SYNC_ENABLED: bool = True
    SCHEDULE_CATEGORY_COUNT_ENABLED: bool = True
    SCHEDULE_CLEANUP_ENABLED: bool = True
    SCHEDULE_SOCIAL_ENABLED: bool = True

    SCHEDULE_SCRAPE_MINUTES: str = "0,30"
    SCHEDULE_AI_MINUTES: str = "5,35"
    SCHEDULE_RANKING_MINUTES: str = "10,40"
    SCHEDULE_AWS_SYNC_MINUTES: str = "15,45"
    SCHEDULE_CATEGORY_MINUTES: str = "20,50"
    SCHEDULE_CLEANUP_MINUTES: str = "25,55"
    SCHEDULE_SOCIAL_MINUTES: str = "12,42"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
