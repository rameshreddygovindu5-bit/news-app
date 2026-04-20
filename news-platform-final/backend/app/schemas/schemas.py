from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============ ENUMS ============

class FlagEnum(str, Enum):
    PENDING = "P"      # Reporter submitted, awaiting admin approval
    NEW = "N"          # Scraped / approved for AI processing
    AI_PROCESSED = "A" # AI rephrased and categorized
    TOP_NEWS = "Y"     # Top 100 ranked
    DELETED = "D"      # Soft deleted

class AiStatusEnum(str, Enum):
    """Tracks AI processing state. Stored in news_articles.ai_status."""
    PENDING = "pending"
    PROCESSING = "processing"
    AI_SUCCESS = "AI_SUCCESS"
    AI_RETRY_SUCCESS = "AI_RETRY_SUCCESS"
    GOOGLE_NEWS_NO_AI = "GOOGLE_NEWS_NO_AI"   # Google News — AI intentionally skipped
    UNPROCESSED_AI_FALLBACK = "UNPROCESSED_AI_FALLBACK"
    REWRITE_FAILED = "REWRITE_FAILED"          # Sent to admin review (flag=P)
    FAILED = "failed"
    COMPLETED = "completed"                    # Legacy — pre-v2 status code


class ScraperTypeEnum(str, Enum):
    RSS = "rss"
    HTML = "html"
    API = "api"
    MANUAL = "manual"
    CNN = "cnn"
    TIMESOFINDIA = "timesofindia"
    ALJAZEERA = "aljazeera"
    ONEINDIA_ENGLISH = "oneindia english"
    GREATANDHRA = "greatandhra"
    EENADU = "eenadu"
    SAKSHI = "sakshi"
    TV9_TELUGU = "tv9 telugu"
    ONEINDIA_TELUGU = "oneindia telugu"
    PRABHANEWS = "prabhanews"
    TELUGU123 = "telugu123"
    TELUGUTIMES_TELUGU = "telugutimes telugu"
    GOOGLENEWS = "googlenews"
    OTHER = "other"

class RoleEnum(str, Enum):
    ADMIN = "admin"
    REPORTER = "reporter"


# ============ NEWS SOURCE SCHEMAS ============

class NewsSourceBase(BaseModel):
    name: str
    url: str
    language: str = "en"
    scraper_type: ScraperTypeEnum = ScraperTypeEnum.RSS
    scraper_config: Dict[str, Any] = {}
    scrape_interval_minutes: int = 60
    ai_processing_interval_minutes: int = 30
    is_enabled: bool = True
    is_paused: bool = False

class NewsSourceCreate(NewsSourceBase):
    pass

class NewsSourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    language: Optional[str] = None
    scraper_type: Optional[ScraperTypeEnum] = None
    scraper_config: Optional[Dict[str, Any]] = None
    scrape_interval_minutes: Optional[int] = None
    ai_processing_interval_minutes: Optional[int] = None
    is_enabled: Optional[bool] = None
    is_paused: Optional[bool] = None

class NewsSourceResponse(NewsSourceBase):
    id: int
    last_scraped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    scraper_config: Optional[Dict[str, Any]] = {}
    scrape_interval_minutes: Optional[int] = 60
    class Config:
        from_attributes = True


# ============ NEWS ARTICLE SCHEMAS ============

class NewsArticleUpdate(BaseModel):
    original_title: Optional[str] = None
    original_content: Optional[str] = None
    rephrased_title: Optional[str] = None
    rephrased_content: Optional[str] = None
    telugu_title: Optional[str] = None
    telugu_content: Optional[str] = None
    category: Optional[str] = None
    slug: Optional[str] = None
    tags: Optional[List[str]] = None
    flag: Optional[FlagEnum] = None
    image_url: Optional[str] = None

class NewsArticleResponse(BaseModel):
    id: int
    source_id: int
    original_title: str
    original_content: Optional[str] = None
    original_url: Optional[str] = None
    original_language: Optional[str] = None
    published_at: Optional[datetime] = None
    translated_title: Optional[str] = None
    translated_content: Optional[str] = None
    rephrased_title: Optional[str] = None
    rephrased_content: Optional[str] = None
    telugu_title: Optional[str] = None
    telugu_content: Optional[str] = None
    category: Optional[str] = None
    slug: Optional[str] = None
    tags: List[str] = []
    content_hash: Optional[str] = None
    is_duplicate: bool
    flag: str
    ai_status: Optional[str] = None  # AI_SUCCESS | AI_RETRY_SUCCESS | GOOGLE_NEWS_NO_AI | REWRITE_FAILED | pending | failed
    rank_score: float = 0
    image_url: Optional[str] = None
    author: Optional[str] = None
    submitted_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    source_name: Optional[str] = None
    class Config:
        from_attributes = True

class NewsArticleListResponse(BaseModel):
    articles: List[NewsArticleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class ManualNewsCreate(BaseModel):
    title: str
    content: str
    category: Optional[str] = "General"
    tags: List[str] = []
    source_id: Optional[int] = None
    image_url: Optional[str] = None

class ArticleApproval(BaseModel):
    action: str  # 'approve', 'approve_direct', 'reject'
    admin_note: Optional[str] = None

class BulkIDs(BaseModel):
    ids: List[int]

class BulkApproval(BaseModel):
    ids: List[int]
    action: str  # 'approve', 'approve_direct', 'reject'


# ============ AUTH SCHEMAS ============

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    role: RoleEnum = RoleEnum.REPORTER

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None


# ============ CATEGORY SCHEMAS ============

class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool
    article_count: int = 0
    class Config:
        from_attributes = True

class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None


# ============ YOUTUBE SCHEMAS ============

class YouTubeProcessRequest(BaseModel):
    url: str
    source_id: Optional[int] = None

class YouTubeProcessResponse(BaseModel):
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    raw_transcript: Optional[str] = None
    transcript_language: Optional[str] = None
    translated_text: Optional[str] = None
    rephrased_title: Optional[str] = None
    rephrased_content: Optional[str] = None
    telugu_title: Optional[str] = None
    telugu_content: Optional[str] = None
    category: Optional[str] = None
    error: Optional[str] = None

class YouTubeSaveRequest(BaseModel):
    video_url: str
    title: str
    content: str
    category: str = "General"
    tags: List[str] = []
    image_url: Optional[str] = None
    source_id: Optional[int] = None
    telugu_title: Optional[str] = None
    telugu_content: Optional[str] = None


# ============ SCHEDULER SCHEMAS ============

class SchedulerLogResponse(BaseModel):
    """
    Scheduler job log entry.
    Field names match JobExecutionLog model columns exactly.
    Aliases provide backward-compatibility for any clients using old names.
    """
    id: int
    job_name: str                        # model: job_name  (was: job_type)
    run_id: Optional[str] = None
    triggered_by: str = "cron"
    status: str
    rows_ok: int = 0                     # model: rows_ok   (was: articles_processed)
    rows_err: int = 0
    error_summary: Optional[str] = None  # model: error_summary (was: error_message)
    started_at: datetime
    ended_at: Optional[datetime] = None  # model: ended_at  (was: completed_at)
    duration_s: Optional[float] = None   # model: duration_s (was: duration_seconds)

    model_config = {"from_attributes": True}

class SchedulerAction(BaseModel):
    action: str
    source_id: Optional[int] = None

class SchedulerConfigResponse(BaseModel):
    scheduler_enabled: bool
    scrape_enabled: bool
    ai_enabled: bool
    ranking_enabled: bool
    social_enabled: bool
    aws_sync_enabled: bool
    category_count_enabled: bool
    cleanup_enabled: bool
    scrape_minutes: str
    ai_minutes: str
    ranking_minutes: str
    social_minutes: str
    aws_sync_minutes: str
    category_minutes: str
    cleanup_minutes: str
    ai_provider_chain: List[str]
    ai_batch_size: int
    ai_concurrency: int
    top_news_count: int
    top_news_max_age_days: int
    top_news_min_per_category: int
    top_news_max_per_category: int

class SchedulerConfigUpdate(BaseModel):
    scrape_enabled: Optional[bool] = None
    ai_enabled: Optional[bool] = None
    ranking_enabled: Optional[bool] = None
    social_enabled: Optional[bool] = None
    aws_sync_enabled: Optional[bool] = None
    category_count_enabled: Optional[bool] = None
    cleanup_enabled: Optional[bool] = None
    scrape_minutes: Optional[str] = None
    ai_minutes: Optional[str] = None
    ranking_minutes: Optional[str] = None
    social_minutes: Optional[str] = None
    aws_sync_minutes: Optional[str] = None
    category_minutes: Optional[str] = None
    cleanup_minutes: Optional[str] = None


# ============ DASHBOARD ============

class DashboardStats(BaseModel):
    total_articles: int = 0
    new_articles: int = 0
    pending_articles: int = 0
    ai_processed: int = 0
    top_news: int = 0
    deleted: int = 0
    duplicates: int = 0
    sources_count: int = 0
    active_sources: int = 0
    source_stats: List[Dict[str, Any]] = []
    category_stats: List[Dict[str, Any]] = []
    recent_scrapes: List[Dict[str, Any]] = []
    daily_trend: List[Dict[str, Any]] = []
