from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Allow runtime mutation (PUT /api/scheduler/config)
    model_config = ConfigDict(env_file=".env", case_sensitive=True, frozen=False)
    # App
    APP_NAME: str = "News Aggregation Platform"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production-abc123xyz"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database — passwords preserved exactly
    DATABASE_URL: str = "postgresql+asyncpg://newsadmin:newspass123@localhost:5432/newsagg"
    DATABASE_URL_SYNC: str = "postgresql://newsadmin:newspass123@localhost:5432/newsagg"
    AWS_DATABASE_URL: str = "postgresql://appuser:PF2026Secure!@#@32.193.27.142:5432/news_db_fe"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Services — keys preserved exactly
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    AI_PROVIDER: str = "ollama"

    # AI Provider priority chain — tried in order, first success wins
    AI_PROVIDER_CHAIN: List[str] = ["gemini", "groq", "ollama", "ollama-glm", "anthropic", "openai"]
    AI_BATCH_SIZE: int = 100
    AI_CONCURRENCY: int = 15
    AI_MAX_RETRIES: int = 2
    AI_SIMILARITY_THRESHOLD: float = 0.90

    # Scraping
    SCRAPE_TIMEOUT: int = 30
    MAX_ARTICLES_PER_SCRAPE: int = 200
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # Processing
    TOP_NEWS_COUNT: int = 100
    TOP_NEWS_MAX_AGE_DAYS: int = 60          # Only articles from last 60 days eligible
    TOP_NEWS_MIN_PER_CATEGORY: int = 3       # Ensure at least 3 per category in top 100
    TOP_NEWS_MAX_PER_CATEGORY: int = 25      # Cap per category to ensure diversity
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.85

    # Social Posting
    SOCIAL_POST_ENABLED: bool = True
    SOCIAL_SITE_URL: str = "https://www.peoples-feedback.com"
    SCHEDULE_SOCIAL_ENABLED: bool = True
    SCHEDULE_SOCIAL_MINUTES: str = "12,42"

    # Facebook Graph API (Page posting)
    FB_PAGE_ACCESS_TOKEN: str = ""
    FB_PAGE_ID: str = ""

    # Instagram Graph API (via Facebook Business)
    IG_BUSINESS_ACCOUNT_ID: str = ""

    # X (Twitter) API v2
    X_API_KEY: str = ""
    X_API_SECRET: str = ""
    X_ACCESS_TOKEN: str = ""
    X_ACCESS_SECRET: str = ""

    # WhatsApp Business API
    WA_PHONE_NUMBER_ID: str = ""
    WA_ACCESS_TOKEN: str = ""
    WA_RECIPIENT_GROUP: str = ""  # comma-separated phone numbers

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]

    # News Sources Filter
    ENABLED_SOURCES: str = ""

    # ─── SCHEDULER FLAGS (each job can be enabled/disabled) ───
    SCHEDULER_ENABLED: bool = True
    SCHEDULE_SCRAPE_ENABLED: bool = True
    SCHEDULE_AI_ENABLED: bool = True
    SCHEDULE_RANKING_ENABLED: bool = True
    SCHEDULE_AWS_SYNC_ENABLED: bool = True
    SCHEDULE_CATEGORY_COUNT_ENABLED: bool = True
    SCHEDULE_CLEANUP_ENABLED: bool = True

    # Scheduler intervals (cron minute values)
    SCHEDULE_SCRAPE_MINUTES: str = "0,30"
    SCHEDULE_AI_MINUTES: str = "5,35"
    SCHEDULE_RANKING_MINUTES: str = "10,40"
    SCHEDULE_AWS_SYNC_MINUTES: str = "15,45"
    SCHEDULE_CATEGORY_MINUTES: str = "20,50"
    SCHEDULE_CLEANUP_MINUTES: str = "25,55"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
