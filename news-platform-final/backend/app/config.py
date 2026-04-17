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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Only fall back to SQLite when DATABASE_URL is the default placeholder
        # and not explicitly set to a real PostgreSQL connection in .env
        if self.DATABASE_URL == "sqlite+aiosqlite:///./newsagg.db":
            pass  # already sqlite, no action needed
        elif "postgresql" in self.DATABASE_URL:
            # Validate that we can actually parse the PostgreSQL URL
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self.DATABASE_URL.replace("+asyncpg", ""))
                if not parsed.hostname:
                    raise ValueError("No hostname in DATABASE_URL")
            except Exception:
                import logging
                logging.getLogger(__name__).warning(
                    "[CONFIG] PostgreSQL URL invalid — falling back to SQLite"
                )
                self.DATABASE_URL = "sqlite+aiosqlite:///./newsagg.db"
                self.DATABASE_URL_SYNC = "sqlite:///./newsagg.db"

    APP_NAME: str = "News Aggregation Platform"
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ── CANONICAL CATEGORIES (master list — keep in sync everywhere) ──
    CATEGORIES: List[str] = [
        "Home", "World", "Politics", "Business", "Tech", "India", "U.S.",
        "Health", "Science", "Entertainment", "Events", "Sports",
        "Surveys", "Polls",
    ]

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./newsagg.db"
    DATABASE_URL_SYNC: str = "sqlite:///./newsagg.db"
    AWS_DB_HOST: str = ""
    AWS_DB_PORT: int = 5432
    AWS_DB_NAME: str = "news_db_fe"
    AWS_DB_USER: str = ""
    AWS_DB_PASSWORD: str = ""

    # ── Redis ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── AI (chain: gemini_primary → gemini_secondary → openai → local → original) ─
    AI_PROVIDER_CHAIN: List[str] = ["gemini", "gemini2", "gemini3", "openai", "local", "original"]
    AI_BATCH_SIZE: int = 200
    AI_CONCURRENCY: int = 8
    AI_MAX_RETRIES: int = 2
    GEMINI_API_KEY: str = "AIzaSyDweaZssdwJRDh7RSC1scmFvRMBtPwOtAY"
    GEMINI_API_KEY_SECONDARY: str = "AIzaSyDOqGA7f69IcEtp5HiNY7NfMoTpFEi7LGw"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Third Gemini key (used as a fallback when primary and secondary are exhausted)
    GEMINI_API_KEY_TERTIARY: str = "AIzaSyArwJeb6Apc4Vq2_3-tCoEe3Q7ik6Kd_F8"

    # ── Scraping ──────────────────────────────────────────────────────
    SCRAPE_TIMEOUT: int = 30
    MAX_ARTICLES_PER_SCRAPE: int = 200
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # ── File Uploads ──────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # ── Deployment Mode ───────────────────────────────────────────────
    # IS_LOCAL_DEV=true: Local machine pushes data TO AWS via sync.
    # IS_LOCAL_DEV=false (EC2): AWS sync is disabled; data is already local.
    IS_LOCAL_DEV: bool = True

    # ── Ranking ───────────────────────────────────────────────────────
    TOP_NEWS_COUNT: int = 500
    TOP_NEWS_MAX_AGE_DAYS: int = 60
    TOP_NEWS_MAX_PER_CATEGORY: int = 80
    TOP_NEWS_MIN_PER_CATEGORY: int = 30   # guarantee min 30 per category
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
