from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey,
    CheckConstraint, ARRAY, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class NewsSource(Base):
    __tablename__ = "news_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    url = Column(String(500), nullable=False)
    language = Column(String(10), nullable=False, default="en")
    scraper_type = Column(String(20), nullable=False, default="rss")
    scraper_config = Column(JSON, default={})
    scrape_interval_minutes = Column(Integer, nullable=False, default=60)
    ai_processing_interval_minutes = Column(Integer, nullable=False, default=30)
    is_enabled = Column(Boolean, nullable=False, default=True)
    is_paused = Column(Boolean, nullable=False, default=False)
    
    # New columns from spec
    credibility_score = Column(Float, default=0.5)  # 0.0 to 1.0
    priority = Column(Integer, default=0)
    
    last_scraped_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    articles = relationship("NewsArticle", back_populates="source", cascade="all, delete-orphan")


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("news_sources.id", ondelete="CASCADE"), nullable=False)

    # Original content
    original_title = Column(Text, nullable=False)
    original_content = Column(Text)
    original_url = Column(String(1000), unique=True)
    original_language = Column(String(10), default="en")
    published_at = Column(DateTime(timezone=True))

    # Translated content
    translated_title = Column(Text)
    translated_content = Column(Text)

    # AI-rephrased content (English)
    rephrased_title = Column(Text)
    rephrased_content = Column(Text)

    # AI-rephrased content (Telugu)
    telugu_title = Column(Text)
    telugu_content = Column(Text)

    # Categorization
    category = Column(String(100))
    slug = Column(String(500), unique=True, index=True)
    tags = Column(ARRAY(String), default=[])

    # Social Media Flags
    is_posted_fb = Column(Boolean, default=False)
    is_posted_ig = Column(Boolean, default=False)
    is_posted_x = Column(Boolean, default=False)
    is_posted_wa = Column(Boolean, default=False)

    # Duplicate detection
    content_hash = Column(String(64), nullable=False, index=True)
    is_duplicate = Column(Boolean, nullable=False, default=False)
    duplicate_of_id = Column(Integer, ForeignKey("news_articles.id"))

    # Processing flag: P=Pending Approval, N=New, A=AI Processed, Y=Top News, D=Deleted
    flag = Column(String(1), nullable=False, default="N", index=True)

    # AI processing status and error tracking
    ai_status = Column(String(20), nullable=False, default="pending", index=True)
    ai_error_count = Column(Integer, nullable=False, default=0)

    # Submission tracking (for reporter-submitted articles)
    submitted_by = Column(String(100))  # username of reporter who submitted

    # Ranking
    rank_score = Column(Float, default=0)

    # Metadata
    image_url = Column(String(1000))
    author = Column(String(255))
    scrape_metadata = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("flag IN ('P', 'N', 'A', 'Y', 'D')", name="valid_flag"),
    )

    source = relationship("NewsSource", back_populates="articles")


class JobExecutionLog(Base):
    __tablename__ = "job_execution_log"

    id = Column(Integer, primary_key=True)
    job_name = Column(String(100), nullable=False)
    run_id = Column(String(50), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))
    status = Column(String(20), nullable=False, default="RUNNING")
    rows_ok = Column(Integer, default=0)
    rows_err = Column(Integer, default=0)
    duration_s = Column(Float)
    error_summary = Column(Text)
    triggered_by = Column(String(50), default="cron")


class PostErrorLog(Base):
    __tablename__ = "post_error_log"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(10), nullable=False)
    error_code = Column(String(50))
    error_message = Column(Text)
    attempt_num = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SyncMetadata(Base):
    __tablename__ = "sync_metadata"

    id = Column(Integer, primary_key=True)
    target = Column(String(50), nullable=False, unique=True)
    last_sync_at = Column(DateTime(timezone=True))
    last_rows_ok = Column(Integer, default=0)
    last_rows_err = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SourceErrorLog(Base):
    __tablename__ = "source_error_log"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer)
    run_id = Column(String(50))
    error_type = Column(String(50))
    error_message = Column(Text)
    http_status = Column(Integer)
    url = Column(String(1000))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255))
    role = Column(String(20), nullable=False, default="admin")
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    article_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Poll(Base):
    __tablename__ = "polls"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(500), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    options = relationship("PollOption", back_populates="poll", cascade="all, delete-orphan")


class PollOption(Base):
    __tablename__ = "poll_options"
    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False)
    option_text = Column(String(255), nullable=False)
    votes_count = Column(Integer, default=0)
    poll = relationship("Poll", back_populates="options")

# Alias for backward compatibility
SchedulerLog = JobExecutionLog
